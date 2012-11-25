import platform
import time
import urllib2
import json
from threading import Thread, Lock
from collections import defaultdict
from copy import copy, deepcopy

from doppler.utils import logger
from doppler.agent.providers import get_providers_from_packages
import doppler.agent.providers.common
import doppler.agent.providers.mac
import doppler.agent.providers.linux

class ValueStore:
    def __init__(self, de_dupe=False):
        self.lock = Lock()
        self.items = []
        self.de_dupe = de_dupe
        self.last_state = {}

    def register(self, event):
        self.collect(event, None)

    def collect(self, name, value, force_collection=False):
        "Add an item to the store. Supports de-duping."

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
    SMALL_INTERVAL_DURATION = 30 * 60

    def __init__(self, api_key, machine_id, hostname, endpoint=None, send_interval=None):
        # Identifiers
        self.api_key = api_key
        self.machine_id = machine_id
        self.hostname = hostname

        # Where to send to
        self.send_interval = send_interval or self.DEFAULT_SEND_INTERVAL
        self.endpoint = endpoint or self.DEFAULT_METRICS_ENDPOINT

        # List of active metrics providers
        self._active_providers = None

        # Thread-safe data structures for collecting metrics and metadata
        self.metrics_store = ValueStore()
        self.states_store = ValueStore(de_dupe=True)
        self.events_store = ValueStore()
        
        # Set up the payload sections
        self.metrics_payload = {}
        self.states_payload = {}
        self.events_payload = {}
        
        # Transmission lock, protecting against dual send
        self.transimission_lock = Lock()
    
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

    def deep_update_dict(self, destination, source):
        for k,v in source.items():
            if isinstance(v, dict):
                if not k in destination or not isinstance(destination[k], dict):
                    destination[k] = {}
                self.deep_update_dict(destination[k], v)
            else:
                destination[k] = v
        return destination

    def add_ts_values(self, payload, values):
        func = lambda: defaultdict(func)
        generated = defaultdict(func)
        for m in values:
            ts, name, value = m
            generated[name]["values"][ts] = value
        returnValue = self.deep_update_dict(payload, generated)
        return returnValue
    
    def add_ts_array(self, payload, values):
        func = lambda: defaultdict(func)
        generated = defaultdict(func)
        for m in values:
            ts, name, value = m
            if "values" not in generated[name]["values"]:
                generated[name]["values"] = [ts]
            else:
                generated[name]["values"].append(ts)
            
        return self.deep_update_dict(payload, generated)

    def start(self):
        if not self.active_providers():
            logger.warning("No metrics providers available")
            return

        # Start all the provider threads
        for provider_class in self.active_providers():
            provider = provider_class(self, self.metrics_store, self.states_store, self.events_store)
            provider.daemon = True
            
            if isinstance(provider.metrics, dict):
                self.deep_update_dict(self.metrics_payload, provider.metrics)
            if isinstance(provider.states, dict):
                self.deep_update_dict(self.states_payload, provider.states)
            if isinstance(provider.events, dict):
                self.deep_update_dict(self.events_payload, provider.events)
            
            on_start = getattr(provider, "on_start", None)
            if callable(on_start):
                provider.on_start()
            
            provider.start()
        
        self.start_time = int(time.time())
        
        # Start the collector's "post to server" loop
        while True:
            # Pace yourselves
            if self.start_time + self.SMALL_INTERVAL_DURATION > int(time.time()):
                time.sleep(min(self.send_interval, 10))
            else:
                time.sleep(self.send_interval)
            
            self.transmit_payload()

    def transmit_payload(self, transmit_all = False):
        with self.transimission_lock:
            time_collected = int(time.time())
            if transmit_all:
                # Collect all metrics, states and events
                metrics = self.metrics_store.items
                states = self.states_store.items
                events = self.events_store.items
            else:
                # Collect all metrics, states and events collected in the past
                metrics = self.metrics_store.get_completed(time_collected)
                states = self.states_store.get_completed(time_collected)
                events = self.events_store.get_completed(time_collected)
            
            self.add_ts_values(self.metrics_payload, metrics)
            self.add_ts_values(self.states_payload, states)
            self.add_ts_array(self.events_payload, events)

            # Attempt to post the snapshots to our server
            body = json.dumps({
                "apiKey": self.api_key,
                "machineId": self.machine_id,
                "hostname": self.hostname,
                "collectedTs": time_collected,
                "sentTs": int(time.time()),
                "metrics": self.metrics_payload,
                "states": self.states_payload,
                "events": self.events_payload
            })

            headers = {
                "Content-Type": "application/json"
            }
            
            request = urllib2.Request(self.endpoint, body, headers)
            response = urllib2.urlopen(request)

            # Check if POST was successful
            if response.code == 200:
                logger.info("Sent payload to %s (%s metrics, %s states, %s events)" % (self.endpoint, len(metrics), len(states), len(events)))

                # Remove sent values from the stores
                self.metrics_store.remove(metrics)
                self.states_store.remove(states)
                self.events_store.remove(events)
                
                # Clear the payloads
                self.metrics_payload.clear()
                self.states_payload.clear()
                self.events_payload.clear()