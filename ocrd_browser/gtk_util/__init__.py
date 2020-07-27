import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gio


class ActionRegistry:
    def __init__(self, for_widget: Gio.ActionMap):
        self.for_widget = for_widget
        self.actions = {}

    def create(self, name, callback=None):
        callback = callback if callback else getattr(self.for_widget, 'on_' + name)
        action: Gio.SimpleAction = Gio.SimpleAction.new(name)
        action.connect("activate", callback)
        self.for_widget.add_action(action)
        self.actions[name] = action
        return action

    def __getitem__(self, item):
        return self.actions[item]
