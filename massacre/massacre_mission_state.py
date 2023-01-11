"""
This Module contains a subset of all active missions which only contain Massacre Missions
"""
from typing import Callable
from massacre.logger_factory import logger
from dataclasses import dataclass

import massacre.mission_repository

@dataclass
class MassacreMission:
    """
    Class defining a Massacre Mission.
    This class is used in the UI to generate a data view
    """
    target_faction: str 
    count: int
    reward: int
    target_system: str
    target_type: str
    source_faction: str
    is_wing: bool
    id: int

    def as_dict(self):
        as_dict = {
            "target_type": self.target_type,
            "mission_id": self.id,
            "target_faction": self.target_faction,
            "count": self.count,
            "reward": self.reward,
            "target_system": self.target_system,
            "source_faction": self.source_faction,
            "is_wing": self.is_wing
        }
        return as_dict


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
    return MassacreMission(
            target_faction, 
            count, 
            reward, 
            target_system, 
            target_type, 
            source_faction, 
            wing, 
            mission_id
        )


massacre_mission_listeners: list[Callable[[dict[int, MassacreMission]], None]] = []

_massacre_mission_store: dict[int, MassacreMission] = {}


def __is_mission_a_massacre_mission(name: str, target_type: str) -> bool:
    """This is the filter-Function defining if a Mission is considered a Massacre-Mission"""
    return name.startswith("Mission_Massacre") and "OnFoot" not in name and target_type


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
        if __is_mission_a_massacre_mission(mission["Name"], mission.get('TargetType', None)):
            relevant_mission_events.append(mission)
    logger.info(f"{len(relevant_mission_events)} of found Missions are Massacre Missions")
    relevant_missions = map(__build_from_event, relevant_mission_events)

    # Push new Mission State to the Massacre Mission Store
    _massacre_mission_store.clear()
    for mission in relevant_missions:
        _massacre_mission_store[mission.id] = mission

    # Emit Event
    for listener in massacre_mission_listeners:
        listener(_massacre_mission_store)


massacre.mission_repository.active_missions_changed_event_listeners.append(__handle_new_missions_state)
