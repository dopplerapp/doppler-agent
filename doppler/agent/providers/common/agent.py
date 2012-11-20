import re
from doppler.agent.providers import Provider, value_for_column, value_for_regex_column, convert_data_unit, first_matching_line

class events(Provider):
    """
    Details certain agent events
    """

    events = {
        "agent.started": {
            "title": "Agent Started",
        }
    }
    interval = None
    
    def begin(self):
        self.event("agent.started")