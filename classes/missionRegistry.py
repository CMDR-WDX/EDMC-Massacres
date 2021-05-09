from classes.massacremission import MassacreMission
from typing import Dict, Any


class MissionRegistry:
    def __init__(self, active_mission_events: dict, listener=None):
        self.__listener = listener
        self.registry = {}
        all_cmdrs = active_mission_events.keys()
        for cmdr in all_cmdrs:
            self.registry[cmdr] = {}
            for mission_id in active_mission_events[cmdr].keys():
                mission_event = active_mission_events[cmdr][mission_id]
                if "Massacre" in mission_event["Name"]:
                    mission = MassacreMission(
                        mission_event["TargetFaction"],
                        mission_event["KillCount"],
                        mission_event["Reward"],
                        mission_event["DestinationSystem"],
                        mission_event["MissionID"],
                        mission_event["Faction"],
                        mission_event["Wing"]
                    )
                    if mission.get_stackable_identifier() not in self.registry[cmdr].keys():
                        self.__add_mission(cmdr, mission)

    def notify_mission_added(self, cmdr: str, mission: MassacreMission):
        if cmdr not in self.registry.keys():
            self.registry[cmdr] = {}
        self.__add_mission(cmdr, mission)
        self.__notify_listener_state_changed()

    def notify_mission_removed(self, cmdr: str, mission_id: int):
        if cmdr not in self.registry.keys():
            return
        # Find the mission that needs removal
        cmdr_missions = self.registry[cmdr]
        # Look at all stacks
        for stack_identifier in cmdr_missions.keys():
            stack: list[MassacreMission] = cmdr_missions[stack_identifier]
            for entry in stack:
                if entry.id == mission_id:
                    # Not sure about how pass by ref / pass by value works in python, so this is a direct access on the
                    # Class Field
                    self.registry[cmdr][stack_identifier].remove(entry)
                    # If as a result, the list is empty, delete the key
                    if len(self.registry[cmdr][stack_identifier]) == 0:
                        del self.registry[cmdr][stack_identifier]

                    self.__notify_listener_state_changed()
                    return

    def __add_mission(self, cmdr: str, mission: MassacreMission):
        if mission.get_stackable_identifier() not in self.registry[cmdr].keys():
            self.registry[cmdr][mission.get_stackable_identifier()] = []
        self.registry[cmdr][mission.get_stackable_identifier()].append(mission)

    def __notify_listener_state_changed(self):
        if self.__listener is not None:
            self.__listener()

    def build_stack_data(self, cmdr: str):
        missions = self.registry[cmdr]

        target_factions_and_count = {}
        source_factions_with_count_and_reward = {}

        for stack_identifier in missions:
            stack: list[MassacreMission] = missions[stack_identifier]
            for mission in stack:
                if mission.target not in target_factions_and_count:
                    target_factions_and_count[mission.target] = {"count": 0, "missions": []}
                target_factions_and_count[mission.target]["count"] += mission.count
                target_factions_and_count[mission.target]["missions"].append(mission)
                if mission.faction not in source_factions_with_count_and_reward:
                    source_factions_with_count_and_reward[mission.faction] = \
                        {"count": 0, "reward": 0, "missions": [], "reward_shareable": 0}
                source_factions_with_count_and_reward[mission.faction]["count"] += mission.count
                source_factions_with_count_and_reward[mission.faction]["reward"] += mission.reward
                source_factions_with_count_and_reward[mission.faction]["missions"].append(mission)
                if mission.wing:
                    source_factions_with_count_and_reward[mission.faction]["reward_shareable"] += mission.reward

        return {
            "missions": missions,
            "targets": target_factions_and_count,
            "sources": source_factions_with_count_and_reward
        }
