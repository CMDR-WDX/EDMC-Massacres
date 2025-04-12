import json
import datetime as dt
from pathlib import Path
from config import config
from massacre.logger_factory import logger

file_location: str

if hasattr(config, 'get_str'):
    # noinspection SpellCheckingInspection
    file_location = config.get_str("journaldir")
else:
    # noinspection SpellCheckingInspection
    file_location = config.get("journaldir")  #type: ignore
if file_location is None or file_location == "":
    file_location = config.default_journal_dir


class MissionEventsLog:

    def __init__(self) -> None:
        self._cmdr = cmdr


def __get_logs_after_timestamp(timestamp: dt.date) -> list[Path]:
    logs_after_timestamp = []

    for log_file in Path(file_location).glob("*.log"):
        if not log_file.is_file():
            continue
        if timestamp < dt.datetime.fromtimestamp(log_file.stat().st_mtime, tz=dt.timezone.utc).date():
            logs_after_timestamp.append(log_file)
    logger.debug(f"Loaded {len(logs_after_timestamp)} Logs for all CMDRs")
    return logs_after_timestamp


# noinspection SpellCheckingInspection
def get_missions_for_all_cmdrs(timestamp: dt.date) -> dict[str, dict[int, dict]]:
    """
    Returns all Missions that a CMDR accepted after the provided timestamp

    **NOTE**: These are not all current missions. Look into the "Missions"-Event under "Active" for active missions.
    Said array only contains mission UUIDs. So it is best to filter for UUIDs that are present in the Dict
    returned by this function.

    :return: Dictionary [CMDR Name, Dictionary[Mission ID, Mission Object]]
    """

    current_name: str = ""
    current_dict: dict[int, dict] = {}
    return_map: dict[str, dict[int, dict]] = {}

    for path in __get_logs_after_timestamp(timestamp):
        logger.debug(f"Opening file {path} ...")

        with open(path, "r", encoding="utf8") as current_log_file:
            line = current_log_file.readline()

            while line != "":
                try:
                    line_as_json = json.loads(line)

                    if line_as_json["event"] == "Commander":
                        if current_name != "" and current_dict is not {}:
                            return_map[current_name] = current_dict

                        name = str(line_as_json["Name"])

                        if current_name != name:
                            current_name = name
                            current_dict = {}

                    if current_name != "":
                        if line_as_json["event"] == "MissionAccepted":
                            current_dict[line_as_json["MissionID"]] = line_as_json
                        elif line_as_json["event"] == "MissionRedirected":
                            mission_id = line_as_json["MissionID"]
                            """
                            This section processes the MissionRedirected event in log files.
                            For massacre missions, the format is consistent. Simply check if the MissionID exists in the original mission list to confirm completion.
                            """
                            if mission_id in current_dict:
                                # missions completed
                                current_dict[mission_id]["is_completed"] = True
                except Exception:
                    logger.warning("An error occurred, skipping line.")
                finally:
                    line = current_log_file.readline()

    if current_name != "" and current_dict is not {}:
        return_map[current_name] = current_dict

    return return_map
