from gi.repository import Gio, GLib


class ActionRegistry:
    def __init__(self, for_widget: Gio.ActionMap):
        self.for_widget = for_widget
        self.actions = {}

    def create(self, name, callback=None, param_type: GLib.Variant = None):
        callback = callback if callback else getattr(self.for_widget, 'on_' + name)
        if param_type is not None:
            action: Gio.SimpleAction = Gio.SimpleAction.new(name, param_type.get_type())
        else:
            action: Gio.SimpleAction = Gio.SimpleAction.new(name)
        action.connect("activate", callback)
        self.for_widget.add_action(action)
        self.actions[name] = action
        return action

    def __getitem__(self, item) -> Gio.SimpleAction:
        return self.actions[item]
