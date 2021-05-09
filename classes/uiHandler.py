import tkinter as tk
from theme import theme


class UIHandler:
    def __init__(self, tk_frame: tk.Frame):
        self.frame = tk.Frame(tk_frame)
        self.cfg_sum = True
        self.cfg_delta = False
        self.cfg_ratio = False
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
            self.__print_ratio(new_state, row_start_sum + 1)
            if len(new_state["targets"]) > 1:
                row_start_warning = row_start_sum + (2 if self.cfg_ratio else 1)
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
        if self.cfg_delta:
            delta = row_data["delta"]
            tk.Label(self.frame, text=delta).grid(row=row_index, column=3, sticky=tk.W)

    def __print_header(self):
        tk.Label(self.frame, text="Faction").grid(row=0, column=0, sticky=tk.W)
        tk.Label(self.frame, text="Kills").grid(row=0, column=1, sticky=tk.W)
        tk.Label(self.frame, text="Payout (Shareable)").grid(row=0, column=2, sticky=tk.W)
        if self.cfg_delta:
            tk.Label(self.frame, text="Δmax").grid(row=0, column=3, sticky=tk.W)

    def __print_sum(self, data: dict, row: int):
        if not self.cfg_sum:
            return
        payouts = float(sum(value["reward"] for value in data.values())) / 1_000_000
        payouts_shareable = float(sum(value["reward_shareable"] for value in data.values())) / 1_000_000
        payouts_str = "{:10.1f}".format(payouts).strip()
        payouts_shareable_str = "{:10.1f}".format(payouts_shareable).strip()
        kills = max(value["count"] for value in data.values())
        tk.Label(self.frame, text="Sum", fg="green").grid(row=row, column=0, sticky=tk.W)
        tk.Label(self.frame, text=kills, fg="green").grid(row=row, column=1, sticky=tk.W)
        tk.Label(self.frame, text=f"{payouts_str}  ({payouts_shareable_str})", fg="green").grid(row=row, column=2, sticky=tk.W)

    def __print_warning(self, sorted_by_target: dict, row: int):
        message_label = tk.Label(self.frame, text="Warning. More than one Target Faction:")
        message_label.config(fg="red")
        message_label.grid(row=row, columnspan=3, column=0, sticky=tk.W)
        for idx, target_key in enumerate(sorted(sorted_by_target.keys())):
            target = sorted_by_target[target_key]
            target_label = tk.Label(self.frame, text=f"{target_key} @ {target['count']} kills.")
            target_label.grid(row=(row + idx + 1), columnspan=3, column=0, sticky=tk.W)

    def push_new_config(self, show_sum: bool, show_delta: bool, show_ratio: bool):
        self.cfg_sum = show_sum
        self.cfg_delta = show_delta
        self.cfg_ratio = show_ratio

    def __print_ratio(self, data: dict, row: int):
        if not self.cfg_ratio:
            return
        message: str
        if len(data["targets"]) > 1:
            message = "Cannot calculate Ratio for more than one target faction"
        else:
            target = next(iter(data["targets"].values()))  # Should only be one entry in the Dictionary
            required_kills = max(value["count"] for value in data["sources"].values())
            total_kills = target["count"]
            payouts = float(sum(value["reward"] for value in data["sources"].values())) / 1_000_000
            payouts_shareable = float(sum(value["reward_shareable"] for value in data["sources"].values())) / 1_000_000

            ratio_as_string = "{:10.1f}".format(float(total_kills)/float(required_kills)).strip()
            reward_per_kill = "{:10.1f}".format(float(payouts)/float(required_kills)).strip()
            reward_per_kill_shareable = "{:10.1f}".format(float(payouts_shareable) / float(required_kills)).strip()
            message = f"Ratio: {ratio_as_string}, Reward: {reward_per_kill} ({reward_per_kill_shareable}) M CR/kill"
        tk.Label(self.frame, text=message, fg="green").grid(row=row, columnspan=4 if self.cfg_delta else 3, column=0, sticky=tk.W)
        pass
