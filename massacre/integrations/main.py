


import tkinter as tk
from typing import Optional
from massacre.integrations.integration import Integration
import myNotebook as nb

from massacre.integrations.example import ExampleIntegration
from massacre.integrations.overlay.integration import OverlayIntegration

__INTEGRATION_CONSTRUCTORS = [ExampleIntegration, OverlayIntegration]
"""
Put all Integration Classes in here
"""

__ACTIVE_INSTANCES: Optional[list[Integration]] = None
__INACTIVE_INSTANCES: Optional[list[tuple[str, Optional[str]]]] = None
"""
used by get_all_active once built

only None as long as not initialized
"""

def __init_state():
    global __ACTIVE_INSTANCES
    global __INACTIVE_INSTANCES
    if __ACTIVE_INSTANCES is None:
        __ACTIVE_INSTANCES = []
        __INACTIVE_INSTANCES = []
        for ctor in __INTEGRATION_CONSTRUCTORS:
            instance: Integration = ctor()
            result = instance.notify_can_be_activated()
            if result is True:
                instance.notify_initialize()
                __ACTIVE_INSTANCES.append(instance)
            else:
                result_val = result if type(result) is str else None
                __INACTIVE_INSTANCES.append((instance.get_name(), result_val))
            
def get_all_active() -> list[Integration]:
    """
    Lazy-Init Function that returns all active Integrations
    """
    __init_state()
    assert __ACTIVE_INSTANCES is not None
    return __ACTIVE_INSTANCES
    

def get_all_inactive() -> list[tuple[str, Optional[str]]]:
    """
    Lazy-Init Function that returns all inactive Integration with an Optional Reason
    """
    __init_state()
    assert __INACTIVE_INSTANCES is not None
    return __INACTIVE_INSTANCES


def notify_about_settings(frame: nb.Frame):

    tk.Label(frame, text="Integrations", fg="darkorange", font=("Unknown", 15)).grid(columnspan=2, padx=2, sticky=tk.W)

    for integration in get_all_active():
        tk.Label(frame, text=f":: {integration.get_name()}", font=("Unknown", 14)).grid(columnspan=2, padx=2, sticky=tk.W)
        integration.notify_settings_start(frame)

    if len(get_all_inactive()) > 0:
        error_label_texts = []
        for name, optional_reason in get_all_inactive():
            reason_text = "Unknown Reason" if optional_reason is None else optional_reason
            error_label_texts.append(f"{name} — {reason_text}")
        error_text = "\n".join(error_label_texts)
        tk.Label(frame, text=f"Following integrations are inactive:\n{error_text}", fg="darkorange", font=("Unknown", 10)).grid(columnspan=2, padx=2, sticky=tk.W)
    
def notify_about_settings_finished():
    for integration in get_all_active():
        integration.notify_settings_finished()
