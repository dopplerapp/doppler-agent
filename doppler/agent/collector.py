import platform
import time
import urllib2
import json
from threading import Thread, Lock
from collections import defaultdict

from doppler.utils import logger
from doppler.agent.providers import get_providers_from_packages
import doppler.agent.providers.common
import doppler.agent.providers.mac
import doppler.agent.providers.linux

class MetricsStore:
    def __init__(self, de_dupe=False):
        self.lock = Lock()
        self.items = []
        self.de_dupe = de_dupe
        self.last_state = {}

    def collect(self, name, value, force_collection=False):
        "Add an item to the store. Supports de-duping of metrics."

        data = (int(time.time()), name, value)
        with self.lock:
            if self.de_dupe and not force_collection and self.last_state.get(name) == value:
                logger.debug("Skipping metrics collection due to de-duping (%s=%s)" % (name,value))
                return

            logger.info("Collecting %s: %s" % (name,value))
            self.items.append(data)
            self.last_state[name] = value

    def get_completed(self, before):
        "Get all items in this store that didn't occur in this second."

        completed_items = []
        with self.lock:
            this_second = int(time.time())
            for item in self.items:
                ts, name, value = item
                if ts < before:
                    completed_items.append(item)

        return completed_items

    def remove(self, items):
        with self.lock:
            for item in items:
                self.items.remove(item)

class Collector:
    DEFAULT_METRICS_ENDPOINT = "http://notify.doppler.io/"
    DEFAULT_SEND_INTERVAL = 30

    def __init__(self, api_key, machine_id, hostname, endpoint):
        # Identifiers
        self.api_key = api_key
        self.machine_id = machine_id
        self.hostname = hostname

        # Where to send to
        self.endpoint = endpoint or self.DEFAULT_METRICS_ENDPOINT

        # List of active metrics providers
        self._active_providers = None

        # Thread-safe data structures for collecting metrics and metadata
        self.metrics_store = MetricsStore()
        self.metadata_store = MetricsStore()
    
        # TODO: Stores should be synced to disk, in case of agent shutdown or ctrl-c
        # See: http://docs.python.org/2/library/shelve.html
    
    def active_providers(self):
        if self._active_providers is None:
            provider_packages = [doppler.agent.providers.common]
            if platform.system() == "Darwin":
                provider_packages.append(doppler.agent.providers.mac)
            elif platform.system() == "Linux":
                provider_packages.append(doppler.agent.providers.linux)
        
            self._active_providers = set(get_providers_from_packages(provider_packages))
        
        return self._active_providers

    def metrics_snapshot(self, completed_metrics):
        snapshot = defaultdict(dict)
        for m in completed_metrics:
            ts, name, value = m
            snapshot[name][ts] = value
        return snapshot

    def start(self):
        if not self.active_providers():
            logger.warning("No metrics providers available")
            return

        # Start all the provider threads
        for provider_class in self.active_providers():
            provider = provider_class(self.metrics_store, self.metadata_store)
            provider.daemon = True
            provider.start()
        
        # Start the collector's "post to server" loop
        while True:
            # Pace yourselves
            time.sleep(self.DEFAULT_SEND_INTERVAL)

            # Collect all metrics and metadata collected in the past
            time_collected = int(time.time())
            completed_metrics = self.metrics_store.get_completed(time_collected)
            completed_metadata = self.metadata_store.get_completed(time_collected)

            # Attempt to post the snapshots to our server
            body = json.dumps({
                "apiKey": self.api_key,
                "machineId": self.machine_id,
                "hostname": self.hostname,
                "collectedTs": time_collected,
                "sentTs": int(time.time()),
                "metrics": self.metrics_snapshot(completed_metrics),
                "metaData": self.metrics_snapshot(completed_metadata),
            })

            headers = {
                "Content-Type": "application/json"
            }

            request = urllib2.Request(self.endpoint, body, headers)
            response = urllib2.urlopen(request)

            # Check if POST was successful
            if response.code == 200:
                logger.info("Sent payload to %s (%s metrics, %s metaData)" % (self.METRICS_ENDPOINT, len(completed_metrics), len(completed_metadata)))

                # Remove sent metrics from the metrics stores
                self.metrics_store.remove(completed_metrics)
                self.metadata_store.remove(completed_metadata)