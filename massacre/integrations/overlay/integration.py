from typing import Optional
from massacre import massacre_settings, ui
from massacre.integrations.integration import Integration
from massacre.integrations.overlay.overlay import Overlay
from massacre.massacre_mission_state import massacre_mission_listeners
from massacre.logger_factory import logger
import tkinter as tk
import myNotebook as nb


from theme import config

class OverlayIntegrationConfig:
    """
    Settings for the Overlay Integration. 
    Follows the same pattern as the primary config store.
    """
    
    def __init__(self) -> None:
        self.prefix = f"{massacre_settings.plugin_name}.integrations.overlay"


    #######################################
    @property
    def overlay_enabled(self):
        return config.get_bool(f"{self.prefix}.overlay_enabled", default=True)
    
    @overlay_enabled.setter
    def overlay_enabled(self, value: bool):
        config.set(f"{self.prefix}.overlay_enabled", value)
    
    #######################################
    @property
    def overlay_ttl(self):
        return config.get_int(f"{self.prefix}.overlay_ttl", default=30)
    
    @overlay_ttl.setter
    def overlay_ttl(self, value: int):
        config.set(f"{self.prefix}.overlay_ttl", value)



class OverlayIntegration(Integration):
    """
    This is the overlay integration. It interacts with the edmcoverlay Python Module
    and sends commands to it to put data into the overlay
    """
    def __init__(self) -> None:
        super().__init__()
        self.__config = OverlayIntegrationConfig()
        self.__settings_temp = {}
        self.__overlay: Optional[Overlay] = None

    


    def notify_can_be_activated(self) -> bool | str:
        """
        Can only be activated if the Python-Module 
        can be imported.
        """
        try:
            import edmcoverlay # pyright: ignore
            # Intentionally unused
            # Throws Error if edmcoverlay cannot be found
            logger.info("edmcoverlay Python-Module found")
            return True
        except:
            logger.info("edmcoverlay Python-Module missing")
            return "edmcoverlay Python-Module missing"


    def notify_initialize(self):
        if self.__config.overlay_enabled and self.__overlay is None:
            self.__overlay = Overlay(self.__config)

            def handle_new_massacre_mission_state(data: dict[int, ui.MassacreMission]):
                data_view = ui.MassacreMissionData(data)
                if self.__overlay is not None:
                    self.__overlay.notify_about_new_massacre_mission_state(data_view)
            
            massacre_mission_listeners.append(handle_new_massacre_mission_state)



    def notify_settings_start(self, frame) -> None:
        self.__settings_temp.clear()
        self.__settings_temp["overlay_enabled"] = tk.BooleanVar(value=self.__config.overlay_enabled)
        self.__settings_temp["overlay_ttl"] = tk.IntVar(value=self.__config.overlay_ttl)

        settings_offset = 5

        nb.Checkbutton(frame, text="Enable overlay", variable=self.__settings_temp["overlay_enabled"]).grid(padx=settings_offset, sticky=tk.W)
        ttl_frame = nb.Frame(frame)
        nb.Label(ttl_frame, text="Overlay TTL:").grid(column=0, row=0, sticky=tk.W)
        nb.Entry(ttl_frame, textvariable=self.__settings_temp["overlay_ttl"]).grid(column=1, row=0, sticky=tk.W, padx=settings_offset)
        ttl_frame.grid(sticky=tk.W, padx=settings_offset)


    def notify_new_event(self, entry) -> None: 
        if entry["event"] == "SendText" and entry["Message"]:
            if entry["Message"].strip() == "!stack" and self.__overlay is not None:
                self.__overlay.update_overlay()

        
    def notify_settings_finished(self) -> None:
        keys = self.__settings_temp.keys()

        if "overlay_enabled" in keys:
            self.__config.overlay_enabled = self.__settings_temp["overlay_enabled"].get()
        if "overlay_ttl" in keys:
            self.__config.overlay_ttl = self.__settings_temp["overlay_ttl"].get()
        
        self.__settings_temp.clear()

    def get_name(self):
        return "Overlay Binding"

