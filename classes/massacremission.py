class MassacreMission:

    def __init__(self, targetfaction: str, killcount: int,
                 reward: int, targetlocation: str, missionid: int, faction: str, is_wing: bool):
        self.target = targetfaction
        self.count = killcount
        self.reward = reward
        self.system = targetlocation
        self.id = missionid
        self.faction = faction
        self.wing = is_wing

    # This will return a "key" that identifies which missions will not stack on top of each other
    def get_stackable_identifier(self):
        return f"{self.faction} attacking {self.target} in {self.system}"

    def __str__(self):
        return self.get_stackable_identifier() + f" for {self.count} kills. Wing={self.wing}"
