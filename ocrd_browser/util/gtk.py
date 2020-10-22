from typing import Callable, Dict, Optional

from gi.repository import Gio, GLib

ActionCallback = Optional[Callable[[Gio.SimpleAction, str], None]]


class ActionRegistry:
    def __init__(self, for_widget: Gio.ActionMap):
        self.for_widget = for_widget
        self.actions: Dict[str, Gio.SimpleAction] = {}

    def create(self, name: str, callback: ActionCallback = None,
               param_type: GLib.VariantType = None, state: GLib.Variant = None) -> Gio.SimpleAction:
        callback = callback if callback else getattr(self.for_widget, 'on_' + name)
        action = Gio.SimpleAction(name=name, parameter_type=param_type, state = state)
        if state:
            action.connect("change-state", callback)
        else:
            action.connect("activate", callback)
        self.for_widget.add_action(action)
        self.actions[name] = action
        return action

    def __getitem__(self, item: str) -> Gio.SimpleAction:
        return self.actions[item]
