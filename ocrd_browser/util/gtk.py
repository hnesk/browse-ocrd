from typing import Callable, Dict, Optional

from gi.repository import Gio, GLib

ActionCallback = Optional[Callable[[Gio.SimpleAction, str], None]]


class ActionRegistry:
    def __init__(self, for_widget: Gio.ActionMap):
        self.for_widget = for_widget
        self.actions: Dict[str, Gio.SimpleAction] = {}

    def create(self, name: str, callback: ActionCallback = None,
               param_type: GLib.Variant = None) -> Gio.SimpleAction:
        callback = callback if callback else getattr(self.for_widget, 'on_' + name)
        parameter_type = param_type.get_type() if param_type is not None else None
        action = Gio.SimpleAction(name=name, parameter_type=parameter_type)
        action.connect("activate", callback)
        self.for_widget.add_action(action)
        self.actions[name] = action
        return action

    def __getitem__(self, item: str) -> Gio.SimpleAction:
        return self.actions[item]
