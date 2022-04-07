import json
import datetime as dt
from datetime import datetime
from pathlib import Path
from logging import Logger
from typing import Dict, Any
from config import config

file_location: str

if hasattr(config, 'get_str'):
    file_location = config.get_str("journaldir")
else:
    file_location = config.get("journaldir")
if file_location is None or file_location == "":
    file_location = config.default_journal_dir


class MissionIndexBuilder:
    def __init__(self, logger: Logger):
        self.__logger = logger
        datetime_of_two_weeks_ago: datetime = dt.datetime.now() - dt.timedelta(weeks=2)
        self._active_mission_events: dict[str, dict[int, Any]] = \
            self.__get_mission_events_of_all_cmdrs_since_timestamp(datetime_of_two_weeks_ago.timestamp())

    """
    Return an Object will all Mission-Related Events, mapped to each commander.
    Dictionary< CMDR Name, Dictionary< TimeStamp, Event > >
    """

    def __get_mission_events_of_all_cmdrs_since_timestamp(self, timestamp_of_event: int):
        list_time_filtered = []  # List of Files that should be checked
        # Filter for time
        x = file_location
        for log_file in Path(file_location).glob("*.log"):
            if not log_file.is_file():
                continue
            time_from_arg = dt.datetime.fromtimestamp(timestamp_of_event, tz=dt.timezone.utc)
            time = dt.datetime.fromtimestamp(log_file.stat().st_mtime, tz=dt.timezone.utc)
            if time_from_arg < time:
                list_time_filtered.append(log_file)

        # This is the return object
        events = {}

        # Iterate over all selected files
        for log_file in list_time_filtered:
            cmdr_from_logs = None
            timestamp_to_event_map = {}
            with open(log_file, "r", encoding="utf8") as opened_file:
                line = opened_file.readline()
                while line != "":
                    try:
                        json_line = json.loads(line)
                        # This should always be parsed, regardless of Timestamp
                        if json_line["event"] == "MissionAccepted":
                            x = 0

                        if json_line["event"] == "Commander":
                            cmdr_from_logs = json_line["Name"]

                        elif json_line["event"] in [
                            "MissionAccepted",
                        ]:
                            timestamp_to_event_map[json_line["timestamp"]] = json_line

                        elif json_line["event"] == "MissionRedirected":
                            # Don't do anything for now.
                            pass
                    except Exception:
                        self.__logger.warning("Failed to read a line. Skipping")
                    finally:
                        line = opened_file.readline()
            if cmdr_from_logs is None:
                self.__logger.warning("Log File with no User. Skipping")
            else:
                # Patch the root object
                if cmdr_from_logs not in events.keys():
                    events[cmdr_from_logs] = {}

                for timestamp_of_event in timestamp_to_event_map.keys():
                    events[cmdr_from_logs][timestamp_of_event] = timestamp_to_event_map[timestamp_of_event]
        return events

    def get_active_mission_events_for_cmdr(self, cmdr: str):
        return self._active_mission_events[cmdr]

    def get_all(self):
        return self._active_mission_events
