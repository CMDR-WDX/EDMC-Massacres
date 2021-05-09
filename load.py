
import logging
import os.path
from logging import Logger
import tkinter as tk
from classes.uiHandler import UIHandler


from typing import Dict, Any, Optional

from classes.alreadyPresentMissionReader import MissionIndexBuilder
from classes.massacremission import MassacreMission
from classes.missionRegistry import MissionRegistry

from config import appname

plugin_name = os.path.basename(os.path.dirname(__file__))

logger: Logger = logging.getLogger(f'{appname}.{plugin_name}')

ui_handler: UIHandler

mission_registry: MissionRegistry


if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s'
    )
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

selected_cmdr: str = ""


def plugin_app(parent: tk.Frame) -> tk.Frame:
    global ui
    ui = UIHandler(parent)
    return ui.frame


def update_ui_with_new_state():
    newState = mission_registry.build_stack_data(selected_cmdr)
    ui.update(newState)


def plugin_start3(plugin_dir: str) -> str:
    global mission_registry
    logger.info(f"Starting up Massacre Plugin. Dir: {plugin_dir}")

    allMissionsStillActive = MissionIndexBuilder(logger)
    mission_registry = MissionRegistry(allMissionsStillActive.get_all(), listener=update_ui_with_new_state)
    return "massacre"


def journal_entry(
        cmdr: str,
        is_beta_: bool,
        system: str,
        station: str,
        entry: Dict[str, Any],
        state: Dict[str, Any]
) -> None:
    global selected_cmdr
    if selected_cmdr != cmdr:
        selected_cmdr = cmdr
        update_ui_with_new_state()
    if entry["event"] == "MissionAccepted" \
            and "Massacre" in entry["Name"] \
            and entry["TargetType"] == "$MissionUtil_FactionTag_Pirate;":
        mission = MassacreMission(
            entry["TargetFaction"],
            entry["KillCount"],
            entry["Reward"],
            entry["DestinationSystem"],
            entry["MissionID"],
            entry["Faction"],
            entry["Wing"]
        )
        mission_registry.notify_mission_added(cmdr, mission)

    # Handle Mission Removal
    if entry["event"] in [
        "MissionCompleted",
        "MissionFailed",
        "MissionAbandoned",
    ]:
        mission_registry.notify_mission_removed(cmdr, entry["MissionID"])
    return


def dashboard_entry(cmdr: str, is_beta: bool, entry: Dict[str, Any]):
    global selected_cmdr
    if selected_cmdr != cmdr:
        selected_cmdr = cmdr
        update_ui_with_new_state()