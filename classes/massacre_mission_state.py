"""
This Module contains a subset of all active missions which only contain Massacre Missions
"""
from typing import Callable
from classes.logger_factory import logger

import classes.mission_repository


class MassacreMission:
    """
    Class defining a Massacre Mission.
    This class is used in the UI to generate a data view
    """
    def __init__(self, target_faction: str, count: int, reward: int, target_system: str, target_type: str,
                 source_faction: str, mission_id: int, wing: bool):
        self._target_faction: str = target_faction
        self._count: int = count
        self._reward: int = reward
        self._target_system: str = target_system
        self._target_type: str = target_type
        self._source_faction: str = source_faction
        self._is_wing: bool = wing
        self._id: int = mission_id

    @property
    def target_type(self):
        return self._target_type

    @property
    def mission_id(self):
        return self._id

    @property
    def target_faction(self):
        return self._target_faction

    @property
    def count(self):
        return self._count

    @property
    def reward(self):
        return self._reward

    @property
    def target_system(self):
        return self._target_system

    @property
    def source_faction(self):
        return self._source_faction

    @property
    def is_wing(self):
        return self._is_wing


def __build_from_event(event: dict) -> MassacreMission:
    """
    Build a Massacre Mission from a MissionAccepted-Event
    """
    target_faction: str = event["TargetFaction"]
    count: int = event["KillCount"]
    reward: int = event["Reward"]
    target_system: str = event["DestinationSystem"]
    target_type: str = event["TargetType"]
    source_faction: str = event["Faction"]
    mission_id: int = event["MissionID"]
    wing: bool = event["Wing"]
    return MassacreMission(target_faction, count, reward, target_system, target_type, source_faction, mission_id, wing)


massacre_mission_listeners: list[Callable[[dict[int, MassacreMission]], None]] = []

_massacre_mission_store: dict[int, MassacreMission] = {}


def __is_mission_a_massacre_mission(name: str) -> bool:
    """This is the filter-Function defining if a Mission is considered a Massacre-Mission"""
    return name.startswith("Mission_Massacre") and "OnFoot" not in name


def __handle_new_missions_state(data: dict[int, dict]):
    """
    Callback used by the Mission Repository to notify this Module about new Missions. This module
    will then filter out non-massacre missions.

    :param data: All missions for this Commander (not just Massacre Missions)
    """
    # Go through all Missions, check if they are Massacre Missions
    logger.info(f"Received a new Missions State with {len(data)} Missions.")
    relevant_mission_events = []
    for mission in data.values():
        if __is_mission_a_massacre_mission(mission["Name"]):
            relevant_mission_events.append(mission)
    logger.info(f"{len(relevant_mission_events)} of found Missions are Massacre Missions")
    relevant_missions = map(__build_from_event, relevant_mission_events)

    # Push new Mission State to the Massacre Mission Store
    _massacre_mission_store.clear()
    for mission in relevant_missions:
        _massacre_mission_store[mission.mission_id] = mission

    # Emit Event
    for listener in massacre_mission_listeners:
        listener(_massacre_mission_store)


classes.mission_repository.active_missions_changed_event_listeners.append(__handle_new_missions_state)
