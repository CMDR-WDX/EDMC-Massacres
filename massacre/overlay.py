import os
from typing import Optional

import massacre.massacre_settings
from massacre.massacre_mission_state import massacre_mission_listeners, MassacreMission
from massacre.massacre_settings import Configuration
from massacre.logger_factory import logger
from massacre.version_check import open_download_page
from theme import theme

class MassacreMissionData:
    """
    Creates a "data-view" for the OVERLAY from all massacre missions. Will be used to create a table-like OVERLAY
    Done to split the calculations from the OVERLAY.
    """
    def __init__(self, massacre_state: dict[int, MassacreMission]):
        self.warnings: list[str] = []
        # Faction -> <Count, Reward, ShareableReward, DistanceToMax>
        target_factions: list[str] = []
        target_types: list[str] = []
        target_systems: list[str] = []
        self.faction_to_count_lookup: dict[str, tuple[int, int, int]] = {}
        self.stack_height = 0
        # This is the second-highest value. This is used to display the second-largest value in the delta-Field using
        # a negative.
        self.before_stack_height = 0
        self.target_sum = 0
        self.reward = 0
        self.shareable_reward = 0

        for mission in massacre_state.values():
            mission_giver = mission.source_faction

            if mission_giver not in self.faction_to_count_lookup.keys():
                self.faction_to_count_lookup[mission_giver] = 0, 0, 0

            kill_count, reward, shareable_reward = self.faction_to_count_lookup[mission_giver]
            kill_count += mission.count
            self.target_sum += mission.count
            reward += mission.reward
            if mission.is_wing:
                shareable_reward += mission.reward

            self.faction_to_count_lookup[mission_giver] = kill_count, reward, shareable_reward

            self.shareable_reward += shareable_reward
            self.reward += reward

            if mission.target_faction not in target_factions:
                target_factions.append(mission.target_faction)

            if mission.target_type not in target_types:
                target_types.append(mission.target_type)

            if mission.target_system not in target_systems:
                target_systems.append(mission.target_system)

            if kill_count > self.stack_height:
                self.stack_height = kill_count

        # Check for Warnings
        if len(target_factions) > 1:
            self.warnings.append(f"Multiple Target Factions: {', '.join(target_factions)}!")
        if len(target_types) > 1:
            self.warnings.append(f"Multiple Target Types: {', '.join(target_types)}!")
        if len(target_systems) > 1:
            self.warnings.append(f"Multiple Target Systems: {', '.join(target_systems)}!")

        # Calculate before_stack_height
        for count, _a, _b in self.faction_to_count_lookup.values():
            if count > self.before_stack_height and count != self.stack_height:
                self.before_stack_height = count
        if self.before_stack_height == 0:  # No other elements. All at max value.
            self.before_stack_height = self.stack_height


class GridOverlaySettings:
    """
    Subset of the entire Configuration that focuses on which information is displayed
    """
    def __init__(self, config: Configuration):
        self.use_overlay = config.display_use_overlay


def __display_data_header(settings: GridOverlaySettings):
    """
    Display the Labels of the Table
    """

    overlay_elements = ['Kills', 'Reward (Wing)', f'{"Faction":15}']

    return overlay_elements


def __display_row(faction: str, data: tuple[int, int, int], max_count: int,
                  settings: GridOverlaySettings, second_largest_count: int):
    """
    Draw one Data-Row for the Table
    """
    count, reward, shareable_reward = data
    reward_str = "{:.1f}".format(float(reward) / 1_000_000)
    shareable_reward_str = "{:.1f}".format(float(shareable_reward) / 1_000_000)
    whole_reward_str = f'{reward_str} ({shareable_reward_str})'
    overlay_elements = [f'{count:4}', f'{whole_reward_str:{len("Reward (Wing)")}}', f'{faction:15}']

    return overlay_elements

def __display_sum(data: MassacreMissionData, _settings: GridOverlaySettings):
    """
    Display the Sum-Row containing the Reward-Sum and the amount of Kills required.
    """
    label = "Sum"
    kill_sum = data.stack_height
    reward_sum_normal = "{:.1f}".format(float(data.reward) / 1_000_000)
    reward_sum_wing = "{:.1f}".format(float(data.shareable_reward) / 1_000_000)
    reward_sum = f"{reward_sum_normal} ({reward_sum_wing})"
    return [f'{kill_sum:4}', f'{reward_sum:{len("Reward (Wing)")}}', f'{"Sum":15}']

def _display_data(data: MassacreMissionData, settings: GridOverlaySettings):
    lines = []
    lines.append('|'.join(__display_data_header(overlay, settings)))
    for faction in sorted(data.faction_to_count_lookup.keys()):
        lines.append('|'.join(__display_row(overlay, faction, data.faction_to_count_lookup[faction], data.stack_height, settings, data.before_stack_height)))

    lines.append('|'.join(__display_sum(overlay, data, settings)))

    lines.extend(data.warnings)

    return lines


def _display_waiting_for_missions():
    return ["Massacre Plugin is ready."]


class Overlay:
    def _create_overlay(self):
        self.__overlay = None
        if self.__settings.use_overlay:
            try:
                import EDMCOverlay
                self.__overlay = EDMCOverlay.Overlay()
            except ModuleNotFoundError:
                logger.warning("Overlay library could not be loaded.")
                
    def __init__(self):
        self.__data: Optional[MassacreMissionData] = None
        self.__settings: GridOverlaySettings = GridOverlaySettings(massacre.massacre_settings.configuration)
        self._create_overlay()
        massacre.massacre_settings.configuration.config_changed_listeners.append(self.rebuild_settings)
                
    def __bool__(self):
        return self.__overlay != None

    def rebuild_settings(self, config: Configuration):
        self.__settings = GridOverlaySettings(config)
        self._create_overlay()
        self.update_overlay()
    
    def notify_about_new_massacre_mission_state(self, data: Optional[MassacreMissionData]):
        self.__data = data
        self.update_overlay()

    def notify_about_settings_changed(self):
        self.__settings: GridOverlaySettings = GridOverlaySettings(massacre.massacre_settings.configuration)
        self._create_overlay()
        self.update_overlay()

    def update_overlay(self):
        if self.__overlay is None:
            logger.warning("Overlay was not yet set. Overlay was not updated.")
            return

        logger.info("Updating Overlay...")

        lines = []
        if self.__data is None:
            pass
        elif self.__data.target_sum == 0:
            lines = _display_waiting_for_missions()
        else:
            lines = _display_data(self.__data, self.__settings)

        if lines:
            self.__overlay.send_message('massacre-update', os.linesep.join(lines), 'yellow', 0, 0, ttl=30)

        logger.info("Overlay Update done")

overlay = Overlay()


def handle_new_massacre_mission_state(data: dict[int, MassacreMission]):
    data_view = MassacreMissionData(data)
    overlay.notify_about_new_massacre_mission_state(data_view)


massacre_mission_listeners.append(handle_new_massacre_mission_state)
