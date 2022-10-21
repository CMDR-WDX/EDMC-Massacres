import json
import datetime as dt
from datetime import datetime
from pathlib import Path
from config import config
from massacre.logger_factory import logger

file_location: str

if hasattr(config, 'get_str'):
    # noinspection SpellCheckingInspection
    file_location = config.get_str("journaldir")
else:
    # noinspection SpellCheckingInspection
    file_location = config.get("journaldir")
if file_location is None or file_location == "":
    file_location = config.default_journal_dir


def __get_logs_after_timestamp(timestamp: dt.date) -> list[Path]:
    logs_after_timestamp = []

    for log_file in Path(file_location).glob("*.log"):
        if not log_file.is_file():
            continue
        if timestamp < dt.datetime.fromtimestamp(log_file.stat().st_mtime, tz=dt.timezone.utc).date():
            logs_after_timestamp.append(log_file)
    logger.debug(f"Loaded {len(logs_after_timestamp)} Logs for all CMDRs")
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
            except Exception:
                logger.warning(f"Failed to open File {file_path}. Skipping...")
            finally:
                line = current_log_file.readline()
        return cmdr, return_list


# noinspection SpellCheckingInspection
def get_missions_for_all_cmdrs(timestamp: dt.date) -> dict[str, dict[int, dict]]:
    """
    Returns all Missions that a CMDR accepted after the provided timestamp

    **NOTE**: These are not all current missions. Look into the "Missions"-Event under "Active" for active missions.
    Said array only contains mission UUIDs. So it is best to filter for UUIDs that are present in the Dict
    returned by this function.

    :return: Dictionary [CMDR Name, Dictionary[Mission ID, Mission Object]]
    """

    # This contains MissionAccepted-events from all CMDRs
    all_mission_logs_after_timestamp_for_all_cmdrs = \
        map(__extract_mission_accepted_events_from_log, __get_logs_after_timestamp(timestamp))

    return_list: dict[str, list[dict]] = {}

    # This contains the events in a normal list
    for cmdr_from_event, events in all_mission_logs_after_timestamp_for_all_cmdrs:
        if cmdr_from_event not in return_list.keys():
            return_list[cmdr_from_event] = []

        return_list[cmdr_from_event].extend(events)

    # Now create a UUID -> Mission Lookup for each CMDR
    return_array: dict[str, dict[int, dict]] = {}

    for cmdr in return_list.keys():
        return_array[cmdr] = {}
        for event in return_list[cmdr]:
            return_array[cmdr][event["MissionID"]] = event


    return return_array
