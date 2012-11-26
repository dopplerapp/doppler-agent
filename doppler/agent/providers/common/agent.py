import signal
from doppler.agent.providers import Provider, value_for_column, value_for_regex_column, convert_data_unit, first_matching_line

class events(Provider):
    """
    Details certain agent events
    """

    events = {
        "agent.started": {
            "title": "Doppler Agent Started",
        },
        "agent.stopped": {
            "title": "Doppler Agent Stopped"
        }
    }
    interval = None
    
    def agent_stopped_handler(self, signum, frame):
        print "Detected agent stop"
        self.event("agent.stopped")
        self.collector.transmit_payload(True)
        exit(0)
    
    def on_start(self):
        # Register for the signals signalling shutdown
        signal.signal(signal.SIGINT, self.agent_stopped_handler)
        signal.signal(signal.SIGTERM, self.agent_stopped_handler)
        self.event("agent.started")
        self.collector.transmit_payload(True)
        
    def begin(self):
        # All events are logged in on_start
        pass