from abc import ABC, abstractmethod

class Integration(ABC):
    """
    This is the Base Class for any Integration. EDMC-Massacre will check which 
    Integrations can be activated on startup. 

    If activation is possible, it will invoke the notify_initialize Method. 

    If the User opens the settings notify_settings_start is invoked. Here the Integration 
    can inject its own settings and commit them when notify_settings_finished is invoked. 
    """

    @abstractmethod
    def notify_can_be_activated(_) -> bool | str:
        """
        This Method should tell the Plugin if this Integration could even run.
        For example the edmcoverlay Integration needs a Python Library to be installed to function properly. 

        Alternatively, this can return a reason as to why this is disabled as a string.
        A string assumes that activation is not possible.
        """
        return False 

    @abstractmethod
    def notify_initialize(self) -> None:
        """
        Do not use the classes' constructor to initialize the Integration, as at that point we do not know yet if 
        the Integration can be activated. Use this Method instead.
        """
        pass

    @abstractmethod
    def notify_settings_start(self, settings_ui) -> None:
        """
        Invoked by the Plugin when the user opens the settings. Add your own settings logic here.
        """ 
        pass

    @abstractmethod
    def notify_settings_finished(self) -> None:
        """
        Invoked by the Plugin when the user is done changing settings. Add settings committing logic here.
        """
        pass

    @abstractmethod 
    def get_name(self) -> str:
        """
        Returns the name of this integration. used in Logs and injected Settings
        """
        pass

    def notify_new_event(self, event) -> None:
        """
        Invoked by the Plugin if there is a new Event passed from EDMC.

        Note that this is intentionally note marked with @abstractmethod as not all integrations are expected to require an event
        """
        pass


    
