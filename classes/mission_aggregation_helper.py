import json
import datetime as dt
from datetime import datetime
from pathlib import Path
from config import config


file_location: str

if hasattr(config, 'get_str'):
    file_location = config.get_str("journaldir")
else:
    file_location = config.get("journaldir")
if file_location is None or file_location == "":
    file_location = config.default_journal_dir


def __get_logs_after_timestamp(timestamp: datetime) -> list[Path]:
    logs_after_timestamp = []

    for log_file in Path(file_location).glob("*.log"):
        if not log_file.is_file():
            continue
        if timestamp < dt.datetime.fromtimestamp(log_file.stat().st_mtime, tz=dt.timezone.utc):
            logs_after_timestamp.append(log_file)
    return logs_after_timestamp


def __extract_mission_accepted_events_from_log(file_path: Path) -> tuple[str, list[dict]]:
    """
    Return all Mission-Accepted events in this file, as well as the CMDR for this log.
    If the log does not contain a CMDR, "" is returned
    """
    cmdr = ""
    return_list = []

    with open(file_path, "r", encoding="utf8") as current_log_file:
        line = current_log_file.readline()
        while line != "":
            try:
                line_as_json = json.loads(line)
                if line_as_json["event"] == "Commander":
                    cmdr = str(line_as_json["Name"])
                if line_as_json["event"] == "MissionAccepted":
                    return_list.append(line_as_json)
            except: IOError
                # TODO: Err Logging
            finally:
                line = current_log_file.readline()
        # if the Commander Event never occurs, return false
        return cmdr, return_list


def get_missions_for_cmdr(cmdr: str, timestamp: datetime) -> dict[str, dict]:
    """
    Returns all Missions that a CMDR accepted after the provided timestamp

    **NOTE**: These are not all current missions. Look into the "Missions"-Event under "Active" for active missions.
    Said array only contains mission UUIDs. So it is best to filter for UUIDs that are present in the Dict
    returned by this function.

    :param cmdr: The selected CMDR
    :param timestamp: Only logs created after that timestamp will be considered
    :return: missions as a dictionary. The Key is the mission UUID
    """

    # This contains MissionAccepted-events from all CMDRs
    all_mission_logs_after_timestamp_for_all_cmdrs = \
        map(__extract_mission_accepted_events_from_log, __get_logs_after_timestamp(timestamp))

    # This contains the events in a normal list
    mission_accepted_linearized: list[dict] = []
    for cmdr_from_event, events in all_mission_logs_after_timestamp_for_all_cmdrs:
        if cmdr_from_event.lower() == cmdr.lower():
            mission_accepted_linearized.extend(events)

    # Now create a UUID -> Mission Lookup
    mission_dict: dict[str,  dict] = {}

    for event in mission_accepted_linearized:
        mission_dict[event["MissionID"]] = event

    return mission_dict
