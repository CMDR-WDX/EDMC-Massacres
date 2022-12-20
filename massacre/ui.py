import json
import tkinter as tk
from typing import Optional

import massacre.massacre_settings
from massacre.massacre_mission_state import massacre_mission_listeners, MassacreMission
from massacre.massacre_settings import Configuration
from massacre.logger_factory import logger
from massacre.version_check import open_download_page
from theme import theme


class MassacreMissionData:
    """
    Creates a "data-view" for the UI from all massacre missions. Will be used to create a table-like UI
    Done to split the calculations from the UI.
    """
    def __init__(self, massacre_state: dict[int, MassacreMission]):
        self.warnings: list[str] = []
        # if Log Level is set to DEBUG, this will output the current Massacre Mission State to the Log File.
        # for easy searching, you can Ctrl+F for "MASSACRE_MISSION_DATA_INPUT" and get the line below that.
        logger.debug("MassacreMissionData input below: MASSACRE_MISSION_DATA_INPUT")
        logger.debug(json.dumps(massacre_state))

        # Faction -> <Count, Reward, ShareableReward, DistanceToMax>
        target_factions: list[str] = []
        """
        A list containing all Target Factions, as in Factions you are meant to 
        kill as part of the mission. This is used to warn the User that they
        have multiple targets and should recheck their stack.
        """
        target_types: list[str] = []
        """
        List of all target types (like Civilian, Pirates, etc). Will warn the User if they 
        have separate stacks.
        """
        target_systems: list[str] = []
        """
        List of all target systems - as in locations where the targets need to be killed.
        This will warn the player that they should recheck their stack.
        """
        self.faction_to_count_lookup: dict[str, tuple[int, int, int]] = {}
        self.stack_height = 0
        """
        The highest amount of kills needed per faction in this stack.
        """
        self.before_stack_height = 0
        """
        The SECOND-highest amount of kills needed per faction in this stack.
        This is used for the delta-Column of the highest Stack to show the negative
        delta towards the second-highest stack.
        """
        self.target_sum = 0
        """
        The amount of total mission kills (not total required kills (see stack_height))
        """
        self.reward = 0
        """
        How much the player should expect in Wing- and Non-Wing Missions
        """
        self.shareable_reward = 0
        """
        How much the player should expect in Wing-Missions
        """

        for mission in massacre_state.values():
            mission_giver = mission.source_faction
            """This is the Faction that handed out the mission"""

            if mission_giver not in self.faction_to_count_lookup.keys():
                """If no Mission from that Faction is known yet, it will first be initialized"""
                self.faction_to_count_lookup[mission_giver] = 0, 0, 0

            kill_count_faction, reward_faction, shareable_reward_faction = self.faction_to_count_lookup[mission_giver]
            """
            Get the currently summed kill count and rewards from this faction. This might contain data
            from previous Missions from that faction, or 0,0,0 if this is the first mission.
            """
            kill_count_faction += mission.count
            self.target_sum += mission.count
            reward_faction += mission.reward
            # Only wing missions are considered for shareable rewards
            if mission.is_wing:
                shareable_reward_faction += mission.reward

            self.faction_to_count_lookup[mission_giver] = kill_count_faction, reward_faction, shareable_reward_faction

            self.shareable_reward += shareable_reward_faction
            self.reward += reward_faction

            ### Add Faction, Target Type and Target System to the list if they are not 
            ### yet present. This will be later used to generate a warning if more than 
            ### one of a type is present. See "Check for Warnings block below"
            if mission.target_faction not in target_factions:
                target_factions.append(mission.target_faction)

            if mission.target_type not in target_types:
                target_types.append(mission.target_type)

            if mission.target_system not in target_systems:
                target_systems.append(mission.target_system)

            if kill_count_faction > self.stack_height:
                self.stack_height = kill_count_faction

        # After all Missions have been handled, iterate through the faction_to_count_lookup to calculate the Total Rewards   
        for _, reward_faction, shareable_reward_faction in self.faction_to_count_lookup.values():
            self.reward += reward_faction
            self.shareable_reward = shareable_reward_faction

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


class GridUiSettings:
    """
    Subset of the entire Configuration that focuses on which information is displayed
    """
    def __init__(self, config: Configuration):
        self.sum = config.display_delta_column
        self.delta = config.display_delta_column
        self.summary = config.display_ratio_and_cr_per_kill_row


def __get_row_width(settings: GridUiSettings) -> int:
    """
    Return how many columns wide the Table is.
    This depends on if the delta-Column should be displayed
    """
    if settings.delta:
        return 4
    return 3


def _display_no_data_info(frame: tk.Frame):
    """
    Generate the warning that is displayed if the Missions-Event has yet to be received.

    Return Row-Pointer for next row
    """

    warning_label = tk.Label(frame, text="Missing Active Mission Data.\n"
                                         "If you are in game, go to main menu and come back")
    warning_label.config(foreground="yellow")
    warning_label.grid(column=0, row=0)

    return 1


def __display_data_header(frame: tk.Frame, settings: GridUiSettings, row=0):
    """
    Display the Labels of the Table
    """

    faction_label = tk.Label(frame, text="Faction")
    kills_label = tk.Label(frame, text="Kills")
    payout_label = tk.Label(frame, text="Reward (Wing)")

    ui_elements = [faction_label, kills_label, payout_label]

    if settings.delta:
        # noinspection SpellCheckingInspection
        delta_label = tk.Label(frame, text="Δmax")
        ui_elements.append(delta_label)

    for i, item in enumerate(ui_elements):
        item.grid(row=row, column=i, sticky=tk.W)


def __display_row(frame: tk.Frame, faction: str, data: tuple[int, int, int], max_count: int,
                  settings: GridUiSettings, row: int, second_largest_count: int):
    """
    Draw one Data-Row for the Table
    """
    count, reward, shareable_reward = data
    reward_str = "{:.1f}".format(float(reward) / 1_000_000)
    shareable_reward_str = "{:.1f}".format(float(shareable_reward) / 1_000_000)

    faction_label = tk.Label(frame, text=faction)
    kills_label = tk.Label(frame, text=count)
    payout_label = tk.Label(frame, text=f"{reward_str} ({shareable_reward_str})")

    ui_elements = [faction_label, kills_label, payout_label]

    if settings.delta:
        # Calculate difference
        delta = max_count - count
        text = delta if delta > 0 else second_largest_count - max_count
        delta_label = tk.Label(frame, text=str(text))
        ui_elements.append(delta_label)
        delta_label.grid(row=row, column=3)

    for i, element in enumerate(ui_elements):
        element.grid(row=row, column=i, sticky=tk.W)


def __display_sum(frame: tk.Frame, data: MassacreMissionData, _settings: GridUiSettings, row: int):
    """
    Display the Sum-Row containing the Reward-Sum and the amount of Kills required.
    """
    label = tk.Label(frame, text="Sum")
    kill_sum = tk.Label(frame, text=data.stack_height)
    reward_sum_normal = "{:.1f}".format(float(data.reward) / 1_000_000)
    reward_sum_wing = "{:.1f}".format(float(data.shareable_reward) / 1_000_000)
    reward_sum = tk.Label(frame, text=f"{reward_sum_normal} ({reward_sum_wing})")
    for i, entry in enumerate([label, kill_sum, reward_sum]):
        entry.config(fg="green")
        entry.grid(row=row, column=i, sticky=tk.W)


def __display_summary(frame: tk.Frame, data: MassacreMissionData, settings: GridUiSettings, row: int):
    ratio_text = "{:.2f}".format(float(data.target_sum)/float(data.stack_height))
    reward_in_millions = float(data.reward) / 1_000_000
    wing_reward_in_millions = float(data.shareable_reward) / 1_000_000
    reward_text = "{:.2f}".format(reward_in_millions/data.stack_height)
    wing_reward_text = "{:.2f}".format(wing_reward_in_millions/data.stack_height)
    label_text = f"Ratio: {ratio_text}, Reward: {reward_text} ({wing_reward_text}) M CR/Kill. {data.target_sum} Kills."

    label = tk.Label(frame, text=label_text, fg="green")
    label.grid(row=row, column=0, columnspan=__get_row_width(settings), sticky=tk.W)


def __display_warning(frame: tk.Frame, warning: str, width: int, row: int):
    label = tk.Label(frame, text=warning)
    label.config(fg="yellow")
    label.grid(column=0, columnspan=width, row=row, sticky=tk.W)


def _display_data(frame: tk.Frame, data: MassacreMissionData, settings: GridUiSettings) -> int:
    __display_data_header(frame, settings)
    row_pointer = 1
    for faction in sorted(data.faction_to_count_lookup.keys()):
        __display_row(frame, faction, data.faction_to_count_lookup[faction], data.stack_height, settings, row_pointer,
                      data.before_stack_height)
        row_pointer += 1

    if settings.sum:
        __display_sum(frame, data, settings, row_pointer)
        row_pointer += 1

    if settings.summary:
        __display_summary(frame, data, settings, row_pointer)
        row_pointer += 1

    full_width = __get_row_width(settings)
    for warning in data.warnings:
        __display_warning(frame, warning, full_width, row_pointer)
        row_pointer += 1

    return row_pointer


def _display_outdated_version(frame: tk.Frame, settings: GridUiSettings, row: int) -> int:
    sub_frame = tk.Frame(frame)
    sub_frame.grid(row=row, column=0, columnspan=__get_row_width(settings))
    sub_frame.config(pady=10)
    tk.Label(sub_frame, text="Massacre Plugin is Outdated").grid(row=0, column=0, columnspan=2)
    btn_github = tk.Button(sub_frame, text="Go to Download", command=open_download_page)
    btn_dismiss = tk.Button(sub_frame, text="Dismiss", command=ui.notify_version_outdated_dismissed)

    for i, item in enumerate([btn_github, btn_dismiss]):
        item.grid(row=1, column=i)
    theme.update(sub_frame)
    return row+1


def _display_waiting_for_missions(frame: tk.Frame):
    tk.Label(frame, text="Massacre Plugin is ready.").grid()
    return 1


class UI:
    def __init__(self):
        self.__frame: Optional[tk.Frame] = None
        self.__data: Optional[MassacreMissionData] = None
        self.__settings: GridUiSettings = GridUiSettings(massacre.massacre_settings.configuration)
        massacre.massacre_settings.configuration.config_changed_listeners.append(self.rebuild_settings)
        self.__display_outdated_version = False

    def rebuild_settings(self, config: Configuration):
        self.__settings = GridUiSettings(config)
        self.update_ui()

    def set_frame(self, frame: tk.Frame):
        self.__frame = tk.Frame(frame)
        self.__frame.grid(column=0, columnspan=frame.grid_size()[1], sticky=tk.W)
        self.__frame.bind("<<Refresh>>", lambda _: self.update_ui())
        self.update_ui()

    def notify_about_new_massacre_mission_state(self, data: Optional[MassacreMissionData]):
        self.__data = data
        self.update_ui()

    def notify_about_settings_changed(self):
        self.__settings: GridUiSettings = GridUiSettings(massacre.massacre_settings.configuration)
        self.update_ui()

    def update_ui(self):
        if self.__frame is None:
            logger.warning("Frame was not yet set. UI was not updated.")
            return

        logger.info("Updating UI...")
        # Remove all the Children in the Frame for rebuild
        for child in self.__frame.winfo_children():
            child.destroy()

        row_pointer = 0
        if self.__data is None:
            row_pointer = _display_no_data_info(self.__frame)
        elif self.__data.target_sum == 0:
            row_pointer = _display_waiting_for_missions(self.__frame)
        else:
            row_pointer = _display_data(self.__frame, self.__data, self.__settings)

        if self.__display_outdated_version:
            row_pointer = _display_outdated_version(self.__frame, self.__settings, row_pointer)

        theme.update(self.__frame)
        logger.info("UI Update done")

    # To be called from thread
    def notify_version_outdated(self):
        self.__display_outdated_version = True
        self.__frame.event_generate("<<Refresh>>")

    # To be called from Button
    def notify_version_outdated_dismissed(self):
        self.__display_outdated_version = False
        self.update_ui()


ui = UI()


def handle_new_massacre_mission_state(data: dict[int, MassacreMission]):
    data_view = MassacreMissionData(data)
    ui.notify_about_new_massacre_mission_state(data_view)


massacre_mission_listeners.append(handle_new_massacre_mission_state)
