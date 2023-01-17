import os
import tkinter
from typing import Any, Optional
from os.path import basename, dirname

from massacre.mission_aggregation_helper import get_missions_for_all_cmdrs

from massacre.ui import ui
from massacre.logger_factory import logger
from massacre.massacre_settings import configuration, build_settings_ui, push_new_changes
from massacre.version_check import build_worker

import massacre.integrations.main as integrations

plugin_name = os.path.basename(os.path.dirname(__file__))
selected_cmdr: Optional[str] = None


def plugin_app(parent: tkinter.Frame) -> tkinter.Frame:
    ui.set_frame(parent)
    # Init Any Integration here
    integrations.get_all_active()

    return parent


def plugin_start3(_: str) -> str:
    logger.info("Stating Massacre Plugin")

    if configuration.check_updates:
        logger.info("Starting Update Check in new Thread...")

        def notify_ui_on_outdated(is_outdated: bool):
            if is_outdated:
                ui.notify_version_outdated()

        thread = build_worker(notify_ui_on_outdated)
        thread.start()
    else:
        logger.info("Skipping Update Check. Disabled in Settings")

    # Building Mission Index
    import datetime as dt
    mission_uuid_to_mission_lookup = get_missions_for_all_cmdrs(dt.date.today() - dt.timedelta(weeks=2))
    logger.info(f"Found Missions for {len(mission_uuid_to_mission_lookup)} CMDRs (completed, finished, failed, etc)")
    from massacre.mission_repository import set_new_repo
    set_new_repo(mission_uuid_to_mission_lookup)

    logger.info("Awaiting CMDR Name to start building Mission Index")
    return basename(dirname(__file__))


def journal_entry(cmdr: str, _is_beta: bool, _system: str,
                  _station: str, entry: dict[str, Any], _state: dict[str, Any]):
    if entry["event"] == "Missions":
        # Fetch the currently active missions and pass them to the Mission Registry
        active_mission_uuids = map(lambda x: int(x["MissionID"]), entry["Active"])
        from massacre.mission_repository import set_active_uuids
        set_active_uuids(list(active_mission_uuids), cmdr)

    elif entry["event"] == "MissionAccepted":
        # A new mission has been accepted. The Mission Repository should be notified about this
        from massacre.mission_repository import mission_repository
        if mission_repository is not None:
            mission_repository.notify_about_new_mission_accepted(entry, cmdr)

    elif entry["event"] in ["MissionAbandoned", "MissionCompleted"]:  # TODO: What about MissionRedirected?
        # Mission has been completed or failed -> It is no longer active
        mission_uuid = entry["MissionID"]
        from massacre.mission_repository import mission_repository
        if mission_repository is not None:
            mission_repository.notify_about_mission_gone(mission_uuid)

    # Pass through the Event to any Integration that needs it
    for integration in integrations.get_all_active():
        try:
           integration.notify_new_event(entry)
        except Exception as e:
            logger.exception(e)
    


def plugin_prefs(parent: Any, _cmdr: str, _is_beta: bool):
    return build_settings_ui(parent)


def prefs_changed(_cmdr: str, _is_beta: bool):
    push_new_changes()
