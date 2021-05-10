from classes.massacremission import MassacreMission

"""
Stores the current "state" of missions
"""


def build_missions_from_events(all_mission_events: dict):
    return_map = {}
    for cmdr_name in all_mission_events.keys():
        array_for_cmdr = []
        for new_mission_event in all_mission_events[cmdr_name].values():
            if "Massacre" in new_mission_event["Name"]:
                array_for_cmdr.append(
                    MassacreMission(
                        new_mission_event["TargetFaction"],
                        new_mission_event["KillCount"],
                        new_mission_event["Reward"],
                        new_mission_event["DestinationSystem"],
                        new_mission_event["MissionID"],
                        new_mission_event["Faction"],
                        new_mission_event["Wing"],
                    )
                )
        return_map[cmdr_name] = array_for_cmdr
    return return_map


def build_stacks_from_mission_array(active_missions):
    returnMap: dict[str, list[MassacreMission]] = {}
    for mission in active_missions:
        stack_identifier = mission.get_stackable_identifier()
        if stack_identifier not in returnMap.keys():
            returnMap[stack_identifier] = []
        returnMap[stack_identifier].append(mission)
    return returnMap


class MissionRegistry:
    def __init__(self, all_mission_events: dict, listener=None):
        self.is_init = False
        self.__listener = listener
        self.registry = {}
        self.__all_missions = build_missions_from_events(all_mission_events)
        self.cmdr = ""

    # Can be called multiple times, e.g. when switching accounts. All missions remain in memory
    def initialize(self, cmdr: str, active_missions_uuids):
        self.cmdr = cmdr
        active_missions = list(filter(lambda x: x.id in active_missions_uuids, self.__all_missions[cmdr]))
        stacks: dict[str, list[MassacreMission]] = build_stacks_from_mission_array(active_missions)
        self.registry = stacks
        self.is_init = True
        self.__notify_listener_state_changed()

    def notify_mission_added(self, cmdr: str, mission: MassacreMission):
        if cmdr != self.cmdr:
            return
        self.__add_mission(mission)
        self.__notify_listener_state_changed()

    def notify_mission_removed(self, cmdr: str, mission_id: int):
        if cmdr != self.cmdr:
            return
        # Find the mission that needs removal
        # Look at all stacks
        for stack_identifier in self.registry.keys():
            stack: list[MassacreMission] = self.registry[stack_identifier]
            for entry in stack:
                if entry.id == mission_id:
                    # Not sure about how pass by ref / pass by value works in python, so this is a direct access on the
                    # Class Field
                    self.registry[stack_identifier].remove(entry)
                    # If as a result, the list is empty, delete the key
                    if len(self.registry[stack_identifier]) == 0:
                        del self.registry[stack_identifier]

                    self.__notify_listener_state_changed()
                    return

    def __add_mission(self, mission: MassacreMission):
        if mission.get_stackable_identifier() not in self.registry.keys():
            self.registry[mission.get_stackable_identifier()] = []
        self.registry[mission.get_stackable_identifier()].append(mission)

    def __notify_listener_state_changed(self):
        if self.__listener is not None:
            self.__listener()

    def build_stack_data(self, cmdr: str):
        if not self.is_init or cmdr != self.cmdr:
            return {}

        target_factions_and_count = {}
        source_factions_with_count_and_reward = {}

        all_counts = []
        # Do a first pass to get the highest and second-highest values
        for stack_identifier in self.registry:
            stack_sum = 0
            for mission in self.registry[stack_identifier]:
                stack_sum += mission.count
            all_counts.append(stack_sum)

        all_counts = sorted(list(set(all_counts)), reverse=True)
        maximum_value = all_counts[0]
        if len(all_counts) >= 2:
            second_highest_value = all_counts[1]
        else:
            second_highest_value = all_counts[0]

        for stack_identifier in self.registry:
            stack: list[MassacreMission] = self.registry[stack_identifier]

            if len(stack) == 0:
                continue

            factionName = stack[0].faction

            for mission in stack:
                if mission.target not in target_factions_and_count:
                    target_factions_and_count[mission.target] = {"count": 0, "missions": []}
                target_factions_and_count[mission.target]["count"] += mission.count
                target_factions_and_count[mission.target]["missions"].append(mission)
                if mission.faction not in source_factions_with_count_and_reward:
                    source_factions_with_count_and_reward[mission.faction] = \
                        {"count": 0, "reward": 0, "missions": [], "reward_shareable": 0}
                source_factions_with_count_and_reward[factionName]["count"] += mission.count
                source_factions_with_count_and_reward[factionName]["reward"] += mission.reward
                source_factions_with_count_and_reward[factionName]["missions"].append(mission)
                if mission.wing:
                    source_factions_with_count_and_reward[factionName]["reward_shareable"] += mission.reward

            delta = maximum_value - source_factions_with_count_and_reward[factionName]["count"]
            if delta == 0:
                delta = second_highest_value - maximum_value
            source_factions_with_count_and_reward[factionName]["delta"] = delta

        return {
            "missions": self.registry,
            "targets": target_factions_and_count,
            "sources": source_factions_with_count_and_reward,
            "max_count": maximum_value,
            "second_max_count": second_highest_value
        }
