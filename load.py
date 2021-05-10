
import logging
import os.path
from logging import Logger
import tkinter as tk
from classes.uiHandler import UIHandler
from config import config
import myNotebook as nb

from typing import Dict, Any, Optional

from classes.alreadyPresentMissionReader import MissionIndexBuilder
from classes.massacremission import MassacreMission
from classes.missionRegistry import MissionRegistry

from config import appname

plugin_name = os.path.basename(os.path.dirname(__file__))

setting_show_sum: Optional[tk.BooleanVar] = None
setting_show_ratio_and_cr_per_kill: Optional[tk.BooleanVar] = None
setting_show_delta_column: Optional[tk.BooleanVar] = None


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
    global ui_handler
    ui_handler = UIHandler(parent)
    # Get config values and fill with defaults if not set

    cfg_sum = config.get_bool(f"{plugin_name}.show_sum")
    cfg_delta = config.get_bool(f"{plugin_name}.show_delta")
    cfg_ratio = config.get_bool(f"{plugin_name}.show_ratio")

    ui_handler.push_new_config(cfg_sum, cfg_delta, cfg_ratio)
    return ui_handler.frame


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
    global setting_show_sum
    global setting_show_delta_column
    global setting_show_ratio_and_cr_per_kill
    setting_show_sum = tk.BooleanVar(value=config.get_bool(f"{plugin_name}.show_sum"))
    setting_show_delta_column = tk.BooleanVar(value=config.get_bool(f"{plugin_name}.show_delta"))
    setting_show_ratio_and_cr_per_kill = tk.BooleanVar(value=config.get_bool(f"{plugin_name}.show_ratio"))
    frame = nb.Frame(parent)
    nb.Label(frame, text="Massacre Plugin Display Settings").grid()
    nb.Checkbutton(frame, text="Display Sum Row", variable=setting_show_sum).grid()
    nb.Checkbutton(frame, text="Display Kill Ratio (*1) and CR per Kill", variable=setting_show_ratio_and_cr_per_kill)\
        .grid()
    nb.Checkbutton(frame, text="Display Delta Column (*2)", variable=setting_show_delta_column).grid()
    nb.Label(frame, text="*1: Calculated as follows: Total Mission Kills / Total required actual kills").grid()
    nb.Label(frame, text="*2: Show the difference to the maximum stack. If it is the maximum stack, the value will"
                         "show the difference to the second highest stack. This value will then prefixed with a '-'")\
        .grid()
    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    config.set(f"{plugin_name}.show_sum", setting_show_sum.get())
    config.set(f"{plugin_name}.show_delta", setting_show_delta_column.get())
    config.set(f"{plugin_name}.show_ratio", setting_show_ratio_and_cr_per_kill.get())
    ui_handler.push_new_config(
        setting_show_sum.get(),
        setting_show_delta_column.get(),
        setting_show_ratio_and_cr_per_kill.get()
    )
    ui_handler.update(mission_registry.build_stack_data(selected_cmdr))


def update_ui_with_new_state():
    newState = mission_registry.build_stack_data(selected_cmdr)
    ui_handler.update(newState)


def plugin_start3(plugin_dir: str) -> str:
    global mission_registry
    logger.info(f"Starting up Massacre Plugin. Dir: {plugin_dir}")
    all_missions_taken_since_2_wks_ago = MissionIndexBuilder(logger)
    mission_registry = MissionRegistry(
        all_missions_taken_since_2_wks_ago.get_all(), listener=update_ui_with_new_state
    )
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
    if entry["event"] == "Missions":
        active_missions = entry["Active"]
        active_mission_ids = list(map(lambda x: x["MissionID"], active_missions))
        mission_registry.initialize(cmdr, active_mission_ids)

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