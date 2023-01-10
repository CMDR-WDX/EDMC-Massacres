"""
This is a basic example on how to create an Integration to Interact with EDMC-Massacre
"""

import threading
from massacre import logger_factory, massacre_settings, ui
from massacre.integrations.integration import Integration
import queue
import tkinter as tk
import myNotebook as nb


from theme import config



class ExampleIntegrationConfig:
    """
    Settings for the Example Integration. 
    Follows the same pattern as the primary config store.
    """
    
    def __init__(self) -> None:
        import massacre.massacre_settings
        self.prefix = f"{massacre_settings.plugin_name}.integrations.example"


    @property
    def is_active(self) -> bool:
        """
        Each Integration should have some type of active-Switch and should be able to get disabled.
        """
        return config.get_bool(f"{self.prefix}.active", default=False)
    
    @is_active.setter
    def is_active(self, val: bool):
        config.set(f"{self.prefix}.active", val)

    @property
    def post_address(self) -> str:
        return config.get_str(f"{self.prefix}.post_address", default="http://localhost:8000/test")

    @post_address.setter
    def post_address(self, val: str):
        config.set(f"{self.prefix}.post_address", val)

class ExampleIntegration(Integration):
    """
    This is a simple example integration. It creates a HTTP Thread and sends mission
    state updates to a Server the user can specify in the Settings.
    """
    def __init__(self) -> None:
        super().__init__()
        self.is_running = False
        self.__http_thread = None
        self.__config = ExampleIntegrationConfig()
        self.__message_queue = queue.Queue()
        self.__settings_temp = {}
        """
        Messages to be sent to the Server. The Worker Thread will block here.
        """
    
    def __worker_thread(self):
        """
        This does NOT run on the main thread!
        """
        from requests import post 
        # Import anything that is not expected to be on every machine
        # inside the scope of a function, not at the top.

        from massacre.ui import MassacreMissionData
        while True:
            try:

                ### Blocking 
                entry: MassacreMissionData = self.__message_queue.get()

                as_dict = {
                    "shareable": entry.shareable_reward,
                    "non_shareable": entry.reward,
                    "missions": map(lambda x: x.__dict__, entry.faction_to_count_lookup.values())
                }

                post(self.__config.post_address, json=as_dict)

            except Exception as ex:
                logger_factory.logger.exception(ex)
            

    def __start_thread(self):
        self.__http_thread = threading.Thread(target=self.__worker_thread, daemon=True, 
                                              name="EDMC-Massacre-Integration-Example-Worker")
        self.__http_thread.start()

    def notify_can_be_activated(self) -> bool:
        #return "The Stars didn't align :c"
        return True; # We just say this can always be activated for the sake of the example. 

    def notify_initialize(self):
        if not self.is_running and self.__config.is_active:
            self.__start_thread()



    def notify_settings_start(self, frame) -> None:
        self.__settings_temp.clear()
        self.__settings_temp["active"] = tk.BooleanVar(value=self.__config.is_active)
        self.__settings_temp["address"] = tk.StringVar(value=self.__config.post_address)

        nb.Checkbutton(frame, text="Activate Integration", variable=self.__settings_temp["active"]).grid(columnspan=2, padx=2, sticky=tk.W)
        nb.Label(frame, text="POST Address").grid(columnspan=2, padx=2, sticky=tk.W)
        nb.Entry(frame, textvariable=self.__settings_temp["address"]).grid(columnspan=2, padx=2, sticky=tk.W)
        
    def notify_settings_finished(self) -> None:
        keys = self.__settings_temp.keys()

        if "active" in keys:
            self.__config.is_active = self.__settings_temp["active"].get()
        if "address" in keys:
            self.__config.post_address = self.__settings_temp["address"].get()
        
        self.__settings_temp.clear()

    def get_name(self):
        return "Example Integration"

