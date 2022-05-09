from enum import Enum
from typing import Callable


class MissionRepoState(Enum):
    AWAITING_INIT = 1
    INITIALIZED = 2


class MissionRepository:
    """
    The Mission Repository contains the current "state" of missions.
    It is built using the historic mission data (see Mission Aggregation Helper) and a "Missions"-Event which contains
    all active / failed / completed missions.

    This was written in a generic manner and as a result is not limited to Massacre Missions
    """

    @property
    def active_missions(self):
        return self._active_missions

    def __init__(self, cmdr: str, missions: dict[str, dict]):
        self._cmdr = cmdr
        self._state = MissionRepoState.AWAITING_INIT
        # The Mission Store contains all missions - REGARDLESS OF IF THEY ARE ACTIVE OR NOT
        self._mission_store = missions

        self._active_missions: dict[str, dict] = {}

        # The listeners are stored as a Tuple of Activator and Callback.
        # Callback: (mission as list of dict) -> void
        self.active_missions_changed_event_listeners: list[Callable[[dict[str, dict]], None]] = []
        self.all_missions_changed_event_listeners: list[Callable[[dict[str, dict]], None]] = []

    def notify_about_active_mission_uuids(self, uuids: list[str]):
        """
        When a "Missions"-Event is found, this should be triggered.
        It should only contain active missions.
        active missions define the intersection between the provided uuids and all missions
        """

        if self._state == MissionRepoState.AWAITING_INIT:
            self._state = MissionRepoState.INITIALIZED
        else:
            # TODO: Log a warning
            pass

        old_active_mission_uuids = sorted(list(self._active_missions.keys()))
        self._active_missions = {}
        for uuid in uuids:
            if uuid in self._mission_store.keys():
                self._active_missions[uuid] = self._mission_store[uuid]
            else:
                # TODO: Log that mission UUID was not found
                pass
        # Afterwards, compare UUIDs. If changes were made, emit an Event
        new_active_mission_uuids = sorted(list(self._active_missions))

        emit_event = False
        if len(old_active_mission_uuids) != len(new_active_mission_uuids):
            emit_event = True
        else:
            # make sure both UUID Lists are identical. UUIDs have been sorted prior
            for i in range(len(new_active_mission_uuids)):
                if old_active_mission_uuids[i] != new_active_mission_uuids[i]:
                    emit_event = True
                    break

        if emit_event:
            for listener in self.active_missions_changed_event_listeners:
                listener(self._active_missions)

