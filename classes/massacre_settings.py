"""
A wrapper around EDMCs Configuration
"""
import os
from classes.logger_factory import logger
from typing import Callable
from config import config


class Configuration:
    
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


configuration = Configuration()
