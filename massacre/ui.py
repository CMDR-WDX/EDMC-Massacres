import json
import l10n
import functools
import tkinter as tk
from typing import Optional
from dataclasses import dataclass
from enum import Enum

import massacre.massacre_settings
from massacre.massacre_mission_state import massacre_mission_listeners, MassacreMission
from massacre.massacre_settings import Configuration
from massacre.logger_factory import logger
from massacre.version_check import open_download_page
from theme import theme

_ = functools.partial(l10n.Translations.translate, context=__file__)

class MassacreMissionData:
    """
    Creates a "data-view" for the UI from all massacre missions. Will be used to create a table-like UI
    Done to split the calculations from the UI.
    """

    @dataclass
    class FactionState:
        @dataclass
        class Entry:
            total: int
            completed: int
            @property
            def remaining(self):
                return self.total - self.completed
            @staticmethod
            def default():
                return MassacreMissionData.FactionState.Entry(0, 0)

        missions: Entry
        kills: Entry
        reward: Entry
        shareable_reward: Entry

        @staticmethod
        def default():
            return MassacreMissionData.FactionState(
                missions = MassacreMissionData.FactionState.Entry.default(),
                kills = MassacreMissionData.FactionState.Entry.default(),
                reward = MassacreMissionData.FactionState.Entry.default(),
                shareable_reward = MassacreMissionData.FactionState.Entry.default(),
            )

    class ColumnType(Enum):
        FACTION = 1
        MISSIONS_OPT = 2
        KILLS = 3
        REWARD = 4
        DELTA_OPT = 5

        def get_alignment_head(self):
            return self.get_alignment_body() # we might change this later. for now "inherit" this from the body

        def get_alignment_body(self):
            if self == MassacreMissionData.ColumnType.FACTION:
                return tk.W
            if self in [
                MassacreMissionData.ColumnType.MISSIONS_OPT,
                MassacreMissionData.ColumnType.KILLS,
                MassacreMissionData.ColumnType.REWARD,
                MassacreMissionData.ColumnType.DELTA_OPT,
            ]:
                return tk.E
            logger.warning("unhandled Column: "+str(self))
            return tk.W

        def get_name(self):
            lookup: dict[MassacreMissionData.ColumnType, str] = {
                MassacreMissionData.ColumnType.FACTION: "Faction",
                MassacreMissionData.ColumnType.MISSIONS_OPT: "Missions",
                MassacreMissionData.ColumnType.KILLS: "Kills",
                MassacreMissionData.ColumnType.REWARD: "Reward (Wing)",
                MassacreMissionData.ColumnType.DELTA_OPT: "Δmax",
            }
            return lookup.get(self, "#MISSING COL DEF")


    def __init__(self, massacre_state: dict[int, MassacreMission]):
        self.warnings: list[str] = []
        # if Log Level is set to DEBUG, this will output the current Massacre Mission State to the Log File.
        # for easy searching, you can Ctrl+F for "MASSACRE_MISSION_DATA_INPUT" and get the line below that.
        logger.debug("MassacreMissionData input below: MASSACRE_MISSION_DATA_INPUT")
        try:
            debug_message_state: dict[int, dict] = {}
            for k in massacre_state.keys():
                v = massacre_state[k]
                debug_message_state[k] = v.as_dict()
            logger.debug(json.dumps(debug_message_state))
        except Exception:
            logger.error("Failed to Log debug_message_state")
            pass
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
        self.faction_to_count_lookup: dict[str, MassacreMissionData.FactionState] = {}
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
        self.mission_count = len(massacre_state.values())
        """
        How many (massacre) missions does the user currently have.
        """
        self.completed_mission_count = 0 # Add the total number of completed missions.
        self.completed_reward = 0 # Add the total rewards from completed missions.
        self.completed_shareable_reward = 0 # Add the total wing mission rewards from completed missions.
        self.completed_kill_count = 0 # Add the total completed kills.

        for mission in massacre_state.values():
            mission_giver = mission.source_faction
            """This is the Faction that handed out the mission"""

            if mission_giver not in self.faction_to_count_lookup.keys():
                """If no Mission from that Faction is known yet, it will first be initialized"""
                self.faction_to_count_lookup[mission_giver] = MassacreMissionData.FactionState.default()

            faction_state = self.faction_to_count_lookup[mission_giver]
            """
            Get the currently summed kill count and rewards from this faction. This might contain data
            from previous Missions from that faction, or 0,0,0 if this is the first mission.
            """
            
            faction_state.missions.total += 1 # Add a count for the number of missions from this faction
            if mission.is_completed: 
                faction_state.missions.completed += 1 # Accumulate the count of completed missions.
                faction_state.kills.completed += mission.count # Accumulate the count of completed kills.
                self.completed_reward += mission.reward # Add rewards from completed missions to the total.
                if mission.is_wing: # Add rewards from completed wing missions to the total.
                    self.completed_shareable_reward += mission.reward

            faction_state.kills.total += mission.count
            self.target_sum += mission.count
            faction_state.reward.total += mission.reward
            # Only wing missions are considered for shareable rewards
            if mission.is_wing:
                faction_state.shareable_reward.total += mission.reward

            ### Add Faction, Target Type and Target System to the list if they are not 
            ### yet present. This will be later used to generate a warning if more than 
            ### one of a type is present. See "Check for Warnings block below"
            if mission.target_faction not in target_factions:
                target_factions.append(mission.target_faction)

            if mission.target_type not in target_types:
                target_types.append(mission.target_type)

            if mission.target_system not in target_systems:
                target_systems.append(mission.target_system)

            if faction_state.kills.total > self.stack_height:
                self.stack_height = faction_state.kills.total

        # After all Missions have been handled, iterate through the faction_to_count_lookup to calculate the Total Rewards   
        for faction_state in self.faction_to_count_lookup.values():
            self.reward += faction_state.reward.total
            self.shareable_reward += faction_state.shareable_reward.total
            self.completed_mission_count += faction_state.missions.completed # Total count of all completed missions (aggregated per faction).
            self.completed_shareable_reward += faction_state.shareable_reward.completed
            # Loop through each faction to find the largest total kills count and use it as the aggregated kill count for all missions
            if faction_state.kills.completed > self.completed_kill_count:
                self.completed_kill_count = faction_state.kills.completed

        # Check for Warnings
        if len(target_factions) > 1:
            self.warnings.append(f"{_('Multiple Target Factions')}: {', '.join(target_factions)}!")
        if len(target_types) > 1:
            self.warnings.append(f"{_('Multiple Target Types')}: {', '.join(target_types)}!")
        if len(target_systems) > 1:
            self.warnings.append(f"{_('Multiple Target Systems')}: {', '.join(target_systems)}!")

        # Calculate before_stack_height
        for faction_state in self.faction_to_count_lookup.values():
            if faction_state.kills.total > self.before_stack_height and faction_state.kills.total != self.stack_height:
                self.before_stack_height = faction_state.kills.total
        if self.before_stack_height == 0:  # No other elements. All at max value.
            self.before_stack_height = self.stack_height


class GridUiSettings:
    """
    Subset of the entire Configuration that focuses on which information is displayed
    """
    def __init__(self, config: Configuration):
        self.has_sum = config.display_sum_row # fix error
        self.has_delta_col = config.display_delta_column
        self.has_summary_row = config.display_ratio_and_cr_per_kill_row
        self.has_mission_count_row = config.display_mission_count
        self.has_missions_col = config.display_missions_column
        self.display_partial_stacks = config.display_partial_stacks

    def get_ordered_columns(self) -> list[MassacreMissionData.ColumnType]:
        return [f for f in [
            MassacreMissionData.ColumnType.FACTION,
            MassacreMissionData.ColumnType.MISSIONS_OPT if self.has_missions_col else None,
            MassacreMissionData.ColumnType.KILLS,
            MassacreMissionData.ColumnType.REWARD,
            MassacreMissionData.ColumnType.DELTA_OPT if self.has_delta_col else None,
        ] if f is not None]



def __get_row_width(settings: GridUiSettings) -> int:
    """
    Return how many columns wide the Table is.
    This depends on if the delta-Column should be displayed
    """
    col_count = 4
    if settings.has_delta_col:
        col_count += 1
    if settings.has_missions_col:
        col_count += 1
    return col_count

def _display_no_data_info(frame: tk.Frame):
    """
    Generate the warning that is displayed if the Missions-Event has yet to be received.

    Return Row-Pointer for next row
    """

    warning_label = tk.Label(frame, text=_("Missing Active Mission Data")+"\n"+_("If you are in game, go to main menu and come back"))
    warning_label.config(foreground="yellow")
    warning_label.grid(column=0, row=0)

    return 1


def __display_data_header(frame: tk.Frame, settings: GridUiSettings, row=0):
    """
    Display the Labels of the Table
    """
    cols = settings.get_ordered_columns()
    for idx, col in enumerate(cols):
        weight = 0
        if col == MassacreMissionData.ColumnType.FACTION:
            weight = 1
        frame.grid_columnconfigure(idx, weight=weight)
        # TODO: Needed?
        # frame.grid_columnconfigure(0, minsize=120, weight=1)
        tk.Label(frame, text=_(col.get_name())).grid(row=row, column=idx, sticky=col.get_alignment_head())
    # todo Check if a toggle button can be inserted here after the faction name.


def __display_row(frame: tk.Frame, faction: str, data: MassacreMissionData.FactionState, max_count: int,
                  settings: GridUiSettings, row: int, second_largest_count: int):
    """
    Draw one Data-Row for the Table
    """
    for i, col_type in enumerate(settings.get_ordered_columns()):
        align = col_type.get_alignment_body()

        match col_type:
            case MassacreMissionData.ColumnType.FACTION:
                text = faction

            case MassacreMissionData.ColumnType.MISSIONS_OPT:
                if settings.display_partial_stacks:
                    text = f"{data.missions.completed}/{data.missions.total}"
                else:
                    text = str(data.missions.total)

            case MassacreMissionData.ColumnType.REWARD:
                # helper to format millions
                def fmt(x):
                    return f"{float(x) / 1_000_000:.1f}"
                total_r = fmt(data.reward.total)
                total_shareable = fmt(data.shareable_reward.total)
                completed_r = fmt(data.reward.completed)
                completed_share = fmt(data.shareable_reward.completed)

                parts = []
                if settings.display_partial_stacks:
                    parts.append(f"{completed_r} ({completed_share})")
                parts.append(f"{total_r} ({total_shareable})")
                text = " / ".join(parts)

            case MassacreMissionData.ColumnType.KILLS:
                parts = []
                if settings.display_partial_stacks:
                    parts.append(str(data.kills.completed))
                parts.append(str(data.kills.total))
                text = "/".join(parts)

            case MassacreMissionData.ColumnType.DELTA_OPT:
                delta = max_count - data.kills.total
                if delta > 0:
                    text = str(delta)
                else:
                    text = str(second_largest_count - max_count)

            case _:
                text = "#MISSING COL DEF"
        tk.Label(frame, text=text).grid(row=row, column=i, sticky=align)


def __display_completed_sum(frame: tk.Frame, data: MassacreMissionData, _settings: GridUiSettings, row: int):
    """
    Add a row to display the total number of currently completed missions.
    """
    label = tk.Label(frame, text=_("Completed Missions"))
    
    completed_num = tk.Label(frame, text=data.completed_mission_count) # Number of completed missions.
    kill_sum = tk.Label(frame, text=data.completed_kill_count) # Number of kills completed in missions.
    reward_sum_normal = "{:.1f}".format(float(data.completed_reward) / 1_000_000)
    reward_sum_wing = "{:.1f}".format(float(data.completed_shareable_reward) / 1_000_000)
    reward_sum = tk.Label(frame, text=f"{reward_sum_normal} ({reward_sum_wing})")
    sticky_settings = [tk.W, tk.E, tk.E, tk.E]
    for i, entry in enumerate([label, completed_num, kill_sum, reward_sum]):
        entry.config(fg="YellowGreen")
        entry.grid(row=row, column=i, sticky=sticky_settings[i])

def __display_sum(frame: tk.Frame, data: MassacreMissionData, settings: GridUiSettings, row: int):
    """
    Display the Sum-Row containing the Reward-Sum and the amount of Kills required.
    """

    for i, col_type in enumerate(settings.get_ordered_columns()):
        align = col_type.get_alignment_body()

        match col_type:
            case MassacreMissionData.ColumnType.FACTION:
                text = _("Summary")

            case MassacreMissionData.ColumnType.MISSIONS_OPT:
                if settings.display_partial_stacks:
                    text = f"{data.completed_mission_count}/{data.mission_count}"
                else:
                    text = str(data.mission_count)

            case MassacreMissionData.ColumnType.REWARD:
                # helper to format millions
                def fmt(x):
                    return f"{float(x) / 1_000_000:.1f}"
                parts = []
                if settings.display_partial_stacks:
                    parts.append(f"{fmt(data.completed_reward)} ({fmt(data.completed_shareable_reward)})")
                parts.append(f"{fmt(data.reward)} ({fmt(data.shareable_reward)})")
                text = " / ".join(parts)

            case MassacreMissionData.ColumnType.KILLS:
                parts = []
                if settings.display_partial_stacks:
                    parts.append(str(data.completed_kill_count))
                parts.append(str(data.stack_height))
                text = "\\".join(parts)

            case MassacreMissionData.ColumnType.DELTA_OPT:
                text = ""

            case _:
                text = "#MISSING COL DEF"
        tk.Label(frame, text=text, fg="green").grid(row=row, column=i, sticky=align)

def __display_summary(frame: tk.Frame, data: MassacreMissionData, settings: GridUiSettings, row: int):
    ratio_text = "{:.2f}".format(float(data.target_sum)/float(data.stack_height))
    reward_in_millions = float(data.reward) / 1_000_000
    wing_reward_in_millions = float(data.shareable_reward) / 1_000_000
    reward_text = "{:.2f}".format(reward_in_millions/data.stack_height)
    wing_reward_text = "{:.2f}".format(wing_reward_in_millions/data.stack_height)
    label_text = f"{_('Ratio')}: {ratio_text}, {_('Reward')}: {reward_text} ({wing_reward_text}) {_('M CR/Kill.')} {data.target_sum} {_('Kills')}."

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
        # todo In the future, add a toggle button here to display detailed mission information under each faction.

    if settings.has_sum:
        __display_sum(frame, data, settings, row_pointer)
        row_pointer += 1

    if settings.has_summary_row:
        __display_summary(frame, data, settings, row_pointer)
        row_pointer += 1
    full_width = __get_row_width(settings)

    if settings.has_mission_count_row:
        __display_mission_count(frame, data, full_width, row_pointer)
        row_pointer += 1

    for warning in data.warnings:
        __display_warning(frame, warning, full_width, row_pointer)
        row_pointer += 1

    return row_pointer


def __display_mission_count(frame: tk.Frame, data: MassacreMissionData, width: int, row: int):
    label = tk.Label(frame, text=f"{_('Mission Count')}: {data.mission_count}/20")
    #label.config(fg="white") # White is hard to see against the default white appearance—switch to blue, light blue, or use EDMC's theme color.
    label.grid(column=0, columnspan=width, row=row, sticky=tk.W)

def _display_outdated_version(frame: tk.Frame, settings: GridUiSettings, row: int) -> int:
    sub_frame = tk.Frame(frame)
    sub_frame.grid(row=row, column=0, columnspan=__get_row_width(settings))
    sub_frame.config(pady=10)
    tk.Label(sub_frame, text=_("Massacre Plugin is Outdated")).grid(row=0, column=0, columnspan=2)
    btn_github = tk.Button(sub_frame, text=_("Go to Download"), command=open_download_page)
    btn_dismiss = tk.Button(sub_frame, text=_("Dismiss"), command=ui.notify_version_outdated_dismissed)

    for i, item in enumerate([btn_github, btn_dismiss]):
        item.grid(row=1, column=i)
    theme.update(sub_frame)
    return row+1


def _display_waiting_for_missions(frame: tk.Frame):
    tk.Label(frame, text=_("Massacre Plugin is ready.")).grid()
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
        # New EDMC Update seems to break frame.grid_size. It returned 0 for EDMC-PVPBot (where I reused the code from here)
        # So it will probably also return 0 here. Someone on the latest version should maybe check it.
        
        # Check if it is 0 and set it to 2. Should probably look into this further at some point.
        cspan = frame.grid_size()[1]
        if cspan < 1:
            cspan = 2
        self.__frame = tk.Frame(frame)
        #self.__frame.config(bg="red") # debug Test layout display.
        self.__frame.grid(column=0, columnspan=cspan, sticky=tk.W)
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
        self.__frame.event_generate("<<Refresh>>") # type: ignore

    # To be called from Button
    def notify_version_outdated_dismissed(self):
        self.__display_outdated_version = False
        self.update_ui()


ui = UI()


def handle_new_massacre_mission_state(data: dict[int, MassacreMission]):
    data_view = MassacreMissionData(data)
    ui.notify_about_new_massacre_mission_state(data_view)


massacre_mission_listeners.append(handle_new_massacre_mission_state)
