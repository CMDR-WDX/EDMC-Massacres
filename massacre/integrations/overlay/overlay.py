from typing import Optional

from massacre.logger_factory import logger
from massacre.ui import MassacreMissionData



def __display_data_header():
    """
    Display the Labels of the Table
    """

    overlay_elements = ['Kills', 'Reward (Wing)', f'{"Faction":15}']

    return overlay_elements


def __display_row(faction: str, data: MassacreMissionData.FactionState):
    """
    Draw one Data-Row for the Table
    """
    reward_str = "{:.1f}".format(float(data.reward) / 1_000_000)
    shareable_reward_str = "{:.1f}".format(float(data.shareable_reward) / 1_000_000)
    whole_reward_str = f'{reward_str} ({shareable_reward_str})'
    overlay_elements = [f'{data.killcount:5}', f'{whole_reward_str:{len("Reward (Wing)")}}', f'{faction:15}']

    return overlay_elements

def __display_sum(data: MassacreMissionData):
    """
    Display the Sum-Row containing the Reward-Sum and the amount of Kills required.
    """
    label = "Sum"
    kill_sum = data.stack_height
    reward_sum_normal = "{:.1f}".format(float(data.reward) / 1_000_000)
    reward_sum_wing = "{:.1f}".format(float(data.shareable_reward) / 1_000_000)
    reward_sum = f"{reward_sum_normal} ({reward_sum_wing})"
    return [f'{kill_sum:5}', f'{reward_sum:{len("Reward (Wing)")}}', f'{"Sum":15}']

def _display_data(data: MassacreMissionData):
    lines = []
    lines.append('|'.join(__display_data_header()))

    lines.append('|'.join(__display_sum(data)))

    for faction in sorted(data.faction_to_count_lookup.keys()):
        lines.append('|'.join(__display_row(faction, data.faction_to_count_lookup[faction])))

    lines.extend(data.warnings)

    return lines


def _display_waiting_for_missions():
    return ["Massacre Plugin is ready."]


class Overlay:
    def _create_overlay(self):
        self.__overlay = None
        if self.__config.overlay_enabled:
            try:
                import edmcoverlay # pyright: ignore
                self.__overlay = edmcoverlay.Overlay()
            except ModuleNotFoundError:
                logger.warning("Overlay library could not be loaded.")
                
    def __init__(self, config):
        self.__config = config
        self.__data: Optional[MassacreMissionData] = None
        self._create_overlay()
                
    def __bool__(self):
        return self.__overlay != None

    def rebuild_settings(self):
        self._create_overlay()
        self.update_overlay()
    
    def notify_about_new_massacre_mission_state(self, data: Optional[MassacreMissionData]):
        self.__data = data
        self.update_overlay()

    def notify_about_settings_changed(self):
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
            lines = _display_data(self.__data)

        line_y = 0
        for line in lines:
            self.__overlay.send_message(f'massacre-line-{line_y}',
                                        line,
                                        'green',
                                        0,
                                        line_y,
                                        ttl=self.__config.overlay_ttl)
            line_y+=20
        
        logger.info("Overlay Update done")





