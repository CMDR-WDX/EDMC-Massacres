"""
A wrapper around EDMCs Configuration
"""
import os
from massacre.logger_factory import logger
from massacre.version_check import download_url
from typing import Callable
from config import config
import tkinter as tk
from tkinter import ttk
from ttkHyperlinkLabel import HyperlinkLabel
# noinspection PyPep8Naming
import myNotebook as nb


class Configuration:
    """
    Abstraction around the config store
    """

    #######################################
    @property
    def check_updates(self):
        return config.get_bool(f"{self.plugin_name}.check_updates", default=True)

    @check_updates.setter
    def check_updates(self, value: bool):
        config.set(f"{self.plugin_name}.check_updates", value)

    #######################################
    @property
    def display_delta_column(self):
        return config.get_bool(f"{self.plugin_name}.display_delta_column", default=True)

    @display_delta_column.setter
    def display_delta_column(self, value: bool):
        config.set(f"{self.plugin_name}.display_delta_column", value)

    #######################################
    @property
    def display_sum_row(self):
        return config.get_bool(f"{self.plugin_name}.display_sum_row", default=True)

    @display_sum_row.setter
    def display_sum_row(self, value: bool):
        config.set(f"{self.plugin_name}.display_sum_row", value)

    #######################################
    @property
    def display_ratio_and_cr_per_kill_row(self):
        return config.get_bool(f"{self.plugin_name}.display_ratio_and_cr_per_kill_row", default=True)

    @display_ratio_and_cr_per_kill_row.setter
    def display_ratio_and_cr_per_kill_row(self, value: bool):
        config.set(f"{self.plugin_name}.display_ratio_and_cr_per_kill_row", value)

    #######################################
    @property
    def display_first_user_help(self):
        return config.get_bool(f"{self.plugin_name}.display_first_user_help", default=True)

    @display_first_user_help.setter
    def display_first_user_help(self, value: bool):
        config.set(f"{self.plugin_name}.display_first_user_help", value)

    def __init__(self):
        self.plugin_name = os.path.basename(os.path.dirname(__file__))
        self.config_changed_listeners: list[Callable[[Configuration], None]] = []

    def notify_about_changes(self, data: dict[str, tk.Variable]):
        keys = data.keys()

        if "check_updates" in keys:
            self.check_updates = data["check_updates"].get()
        if "display_delta_column" in keys:
            self.display_delta_column = data["display_delta_column"].get()
        if "display_sum_row" in keys:
            self.display_sum_row = data["display_sum_row"].get()
        if "display_ratio_and_cr_per_kill_row" in keys:
            self.display_ratio_and_cr_per_kill_row = data["display_ratio_and_cr_per_kill_row"].get()

        for listener in self.config_changed_listeners:
            listener(self)
        

configuration = Configuration()


__setting_changes: dict[str, tk.Variable] = {}
"""
Changes made in the Prefs-UI are stored here. If EDMC notifies the plugin that changes have been applied values from
this dict are then applied to the config.
"""


def push_new_changes():
    """Callback to be used when the user has closed the Settings. This applies changes to the Config."""
    configuration.notify_about_changes(__setting_changes)
    __setting_changes.clear()


def build_settings_ui(root: nb.Notebook) -> tk.Frame:
    """
    Builds the UI for the Prefs-Tab for this Plugin.
    """
    checkbox_offset = 10
    title_offset = 20

    frame = nb.Frame(root) #type: ignore
    frame.columnconfigure(1, weight=1)
    __setting_changes.clear()
    __setting_changes["check_updates"] = \
        tk.IntVar(value=configuration.check_updates)
    __setting_changes["display_delta_column"] = \
        tk.IntVar(value=configuration.display_delta_column)
    __setting_changes["display_sum_row"] = \
        tk.IntVar(value=configuration.display_sum_row)
    __setting_changes["display_ratio_and_cr_per_kill_row"] = \
        tk.IntVar(value=configuration.display_ratio_and_cr_per_kill_row)

    nb.Label(frame, text="UI Settings", pady=10).grid(sticky=tk.W, padx=title_offset)
    ui_settings_checkboxes = [
        nb.Checkbutton(frame, text="Display Delta-Column",
                       variable=__setting_changes["display_delta_column"]),
        nb.Checkbutton(frame, text="Display Sum-Row",
                       variable=__setting_changes["display_sum_row"]),
        nb.Checkbutton(frame, text="Display Summary-Row",
                       variable=__setting_changes["display_ratio_and_cr_per_kill_row"])
    ]
    for entry in ui_settings_checkboxes:
        entry.grid(columnspan=2, padx=checkbox_offset, sticky=tk.W)

    nb.Label(frame, text="Other", pady=10, padx=title_offset).grid(sticky=tk.W)
    nb.Checkbutton(frame, text="Check for Updates on Start", variable=__setting_changes["check_updates"])\
        .grid(columnspan=2, sticky=tk.W, padx=checkbox_offset)
    nb.Label(frame, text="", pady=10).grid()
    nb.Label(frame, text="Made by CMDR WDX").grid(sticky=tk.W, padx=checkbox_offset)
    HyperlinkLabel(frame, text="Github", background=nb.Label().cget("background"), url=download_url, underline=True)\
        .grid(columnspan=2, sticky=tk.W, padx=checkbox_offset)

    return frame
