import datetime
import os
import tkinter
from typing import Optional

import classes.mission_aggregation_helper
import classes.massacre_mission_state

from classes.ui import ui
from classes.logger_factory import logger
from classes.massacre_settings import configuration, build_settings_ui, push_new_changes
from classes.version_check import build_worker

plugin_name = os.path.basename(os.path.dirname(__file__))
selected_cmdr: Optional[str] = None


def plugin_app(parent: tkinter.Frame) -> tkinter.Frame:
    ui.set_frame(parent)
    return parent


def plugin_start3(path: str) -> str:
    logger.info("Stating Massacre Plugin")

    if configuration.check_updates:
        logger.info("Starting Update Check in new Thread...")

        def notify_ui_on_outdated(is_outdated: bool):
            if is_outdated:
                ui.notify_version_outdated()

        thread = build_worker(notify_ui_on_outdated)
        thread.start()


    logger.info("Awaiting CMDR Name to start building Mission Index")
    return "massacre"


def dashboard_entry(cmdr: str, is_beta: bool, entry: dict[str, any]):
    global selected_cmdr
    if selected_cmdr != cmdr:
        selected_cmdr = cmdr
        logger.info(f"New CMDR \"{cmdr}\" found. Rebuilding Mission Index")
        # Rebuilding Mission Index
        import datetime as dt
        mission_uuid_to_mission_lookup = \
            classes.mission_aggregation_helper.get_missions_for_cmdr(cmdr, dt.date.today() - dt.timedelta(weeks=2))
        logger.info(f"Found {len(mission_uuid_to_mission_lookup)} Missions (completed, finished, failed, etc)")
        from classes.mission_repository import set_new_repo
        set_new_repo(cmdr, mission_uuid_to_mission_lookup)


def journal_entry(cmdr: str, is_beta: bool, system: str, station: str, entry: dict[str, any], state: dict[str, any]):

    if entry["event"] == "Missions":
        # Fetch the currently active missions and pass them to the Mission Registry
        active_mission_uuids = map(lambda x: int(x["MissionID"]), entry["Active"])
        from classes.mission_repository import set_active_uuids
        set_active_uuids(list(active_mission_uuids))

    elif entry["event"] == "MissionAccepted":
        # A new mission has been accepted. The Mission Repository should be notified about this
        from classes.mission_repository import mission_repository
        mission_repository.notify_about_new_mission_accepted(entry)

    elif entry["event"] in ["MissionAbandoned", "MissionCompleted"]:  # TODO: What about MissionRedirected?
        # Mission has been completed or failed -> It is no longer active
        mission_uuid = entry["MissionID"]
        from classes.mission_repository import mission_repository
        mission_repository.notify_about_mission_gone(mission_uuid)


def plugin_prefs(parent: any, cmdr: str, is_beta: bool):
    return build_settings_ui(parent)


def prefs_changed(cmdr: str, is_beta: bool):
    push_new_changes()

