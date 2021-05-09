import tkinter as tk
from theme import theme


class UIHandler:
    def __init__(self, tk_frame: tk.Frame):
        self.frame = tk.Frame(tk_frame)
        tk.Label(self.frame, text="Awaiting Initialization...").grid(row=0, column=0)
        theme.update(self.frame)

    def update(self, new_state):
        for child in self.frame.winfo_children():
            child.destroy()
        if len(new_state["missions"]) == 0:
            tk.Label(self.frame, text="Massacre Plugin: No Missions").grid(column=0, row=0)
        else:
            self.__print_header()
            for idx, faction in enumerate(sorted(new_state["sources"].keys())):
                self.__print_row(faction, new_state["sources"][faction], idx + 1)
            row_start_sum = len(new_state["sources"]) + 1
            self.__print_sum(new_state["sources"], row_start_sum)
            if len(new_state["targets"]) > 1:
                row_start_warning = row_start_sum + 1
                self.__print_warning(new_state["targets"], row_start_warning)
        theme.update(self.frame)

    def __print_row(self, faction_name: str, row_data: dict, row_index):
        reward_float = float(row_data["reward"]) / 1_000_000
        reward_float_str = "{:10.1f}".format(reward_float).strip()
        reward_shareable_float = float(row_data["reward_shareable"]) / 1_000_000
        reward_shareable_float_str = "{:10.1f}".format(reward_shareable_float).strip()
        tk.Label(self.frame, text=faction_name).grid(row=row_index, column=0, sticky=tk.W)
        tk.Label(self.frame, text=row_data["count"]).grid(row=row_index, column=1, sticky=tk.W)
        tk.Label(self.frame, text=f"{reward_float_str}  ({reward_shareable_float_str})")\
            .grid(row=row_index, column=2, sticky=tk.W)

    def __print_header(self):
        frame = self.frame
        tk.Label(frame, text="Faction").grid(row=0, column=0, sticky=tk.W)
        tk.Label(frame, text="Kills").grid(row=0, column=1, sticky=tk.W)
        tk.Label(frame, text="Payout (Shareable)").grid(row=0, column=2, sticky=tk.W)
        frame.update()

    def __print_sum(self, data: dict, row: int):
        frame = self.frame
        payouts = float(sum(value["reward"] for value in data.values())) / 1_000_000
        payouts_shareable = float(sum(value["reward_shareable"] for value in data.values())) / 1_000_000
        payouts_str = "{:10.1f}".format(payouts).strip()
        payouts_shareable_str = "{:10.1f}".format(payouts_shareable).strip()
        kills = max(value["count"] for value in data.values())
        tk.Label(frame, text=kills).grid(row=row, column=1, sticky=tk.W)
        tk.Label(frame, text=f"{payouts_str}  ({payouts_shareable_str})").grid(row=row, column=2, sticky=tk.W)

    def __print_warning(self, sorted_by_target: dict, row: int):
        frame = self.frame
        message_label = tk.Label(frame, text="Warning. More than one Target Faction:")
        message_label.config(fg="red")
        message_label.grid(row=row, columnspan=3, column=0, sticky=tk.W)
        for idx, target_key in enumerate(sorted(sorted_by_target.keys())):
            target = sorted_by_target[target_key]
            target_label = tk.Label(frame, text=f"{target_key} @ {target['count']} kills.")
            target_label.grid(row=(row + idx + 1), columnspan=3, column=0, sticky=tk.W)
