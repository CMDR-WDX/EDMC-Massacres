from enum import Flag
from typing import Callable, Optional
from massacre.logger_factory import logger

# The listeners are stored as a Tuple of Activator and Callback.
# Callback: (mission as dict<mission_uuid, mission>) -> void
active_missions_changed_event_listeners: list[Callable[[dict[int, dict]], None]] = []
all_missions_changed_event_listeners: list[Callable[[dict[int, dict]], None]] = []

_active_uuids_init = False
_active_uuids: list[int] = []


class MissionRepoState(Flag):
    AWAITING_INIT = 0b00
    HAS_MISSION_DATA = 0b10
    HAS_MISSIONS_EVENT = 0b01
    INITIALIZED = 0b11


class MissionRepository:
    """
    The Mission Repository contains the current "state" of missions.
    It is built using the historic mission data (see Mission Aggregation Helper) and a "Missions"-Event which contains
    all active / failed / completed missions.

    This was written in a generic manner and as a result is not limited to Massacre Missions
    This was written with multi-cmdr-support in mind.
    """

    @property
    def state(self):
        return self._state

    @property
    def active_missions(self):
        return self._active_missions

    def __init__(self, mission_store: dict[str, dict[int, dict]], cmdr: Optional[str] = None):
        self._cmdr = cmdr
        self._state = MissionRepoState.AWAITING_INIT
        """
        The Mission Repo State. The Repo is fully initialized once the Mission Data (contains all CMDRs) and 
        the Missions-Event (for specific CMDR) are passed.
        """

        self._mission_store: dict[str, dict[int, dict]] = mission_store
        """
        The Mission Store contains all missions - REGARDLESS OF IF THEY ARE ACTIVE OR NOT
        
        Note that this contains Data for all Commanders.  
        The first key is the CMDR, the second key is the Mission UUID
        """
        self._state |= MissionRepoState.HAS_MISSION_DATA
        """
        Preparations for when and if the Mission Aggregation happens in another thread
        """

        self._active_missions: dict[int, dict] = {}
        """Active Missions are just for the current commander"""

        global _active_uuids, _active_uuids_init
        if _active_uuids_init:
            self.notify_about_active_mission_uuids(_active_uuids, cmdr)

    def notify_about_active_mission_uuids(self, uuids: list[int], cmdr: str):
        """
        When a "Missions"-Event is found, this should be triggered.
        It should only contain active missions.
        active missions define the intersection between the provided uuids and all missions
        """
        self._cmdr = cmdr

        if cmdr is None:
            logger.error("Passed CMDR is None! Aborting")
            return

        if self._state & MissionRepoState.HAS_MISSIONS_EVENT == 0:
            self._state |= MissionRepoState.HAS_MISSIONS_EVENT
        else:
            logger.warning("Mission UUIDs were passed even though the State is already initialized")
            pass

        self._active_missions = {}

        all_known_uuids = list(self._mission_store[cmdr].keys())
        for uuid in uuids:
            if uuid in all_known_uuids:
                self._active_missions[uuid] = self._mission_store[cmdr][uuid]
            else:
                logger.warning("A Mission could not be found in the Store even though the UUID is present")
                pass

        #  Emit an Event notifying that the pool of active missions has changed
        #  The listeners should be CMDR-agnostic. They just get the active mission list.
        for listener in active_missions_changed_event_listeners:
            listener(self._active_missions)

    def notify_about_new_mission_accepted(self, mission: dict, cmdr: str):
        logger.info(f"New Mission with ID {mission['MissionID']} has been accepted")
        self._mission_store[cmdr][mission["MissionID"]] = mission
        self._active_missions[mission["MissionID"]] = mission
        self.update_all_listeners()

    def notify_about_mission_gone(self, mission_uuid: int):
        # Should be called when the Mission is handed in or when the Mission has failed
        logger.info(f"Mission with ID {mission_uuid} has been removed")
        del self._active_missions[mission_uuid]
        global active_missions_changed_event_listeners
        for listener in active_missions_changed_event_listeners:
            listener(self._active_missions)

    def update_all_listeners(self):
        global active_missions_changed_event_listeners, all_missions_changed_event_listeners
        for listener in active_missions_changed_event_listeners:
            listener(self._active_missions)
        for listener in all_missions_changed_event_listeners:
            listener(self._mission_store[self._cmdr])


mission_repository: Optional[MissionRepository] = None


def set_new_repo(missions: dict[str, dict[int, dict]]):
    global mission_repository
    mission_repository = MissionRepository(missions)


def set_active_uuids(uuids: list[int], cmdr: str):
    global _active_uuids, _active_uuids_init
    _active_uuids.clear()
    _active_uuids.extend(uuids)
    _active_uuids_init = True

    if mission_repository is not None:
        mission_repository.notify_about_active_mission_uuids(_active_uuids, cmdr)
