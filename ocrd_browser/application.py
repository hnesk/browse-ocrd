from gi.repository import Gio, Gtk, GLib

import pkg_resources
from typing import List
from ocrd_browser.util.gtk import ActionRegistry
from ocrd_browser.ui import MainWindow, AboutDialog, OpenDialog
from ocrd_browser.view import ViewRegistry


class OcrdBrowserApplication(Gtk.Application):
    def __init__(self) -> None:
        Gtk.Application.__init__(self, application_id='org.readmachine.ocrd-browser',
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.actions = ActionRegistry(for_widget=self)
        self.view_registry = ViewRegistry.create_from_entry_points()

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self.actions.create('new')
        self.actions.create('open')
        self.actions.create('about')
        self.actions.create('quit')
        for entry_point in pkg_resources.iter_entry_points('ocrd_browser_ext'):
            (entry_point.load())(self)

    def do_activate(self) -> None:
        win = self.get_active_window()
        if not win:
            win = MainWindow(application=self)
        win.present()

    def on_about(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        about_dialog = AboutDialog(application=self, transient_for=self.get_active_window(), modal=True)
        about_dialog.present()

    def on_quit(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        self.quit()

    def on_open(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        open_dialog = OpenDialog(application=self, transient_for=self.get_active_window(), modal=True)
        response = open_dialog.run()
        if response == Gtk.ResponseType.OK:
            self.open_in_window(open_dialog.get_uri(), window=open_dialog.get_transient_for())
        open_dialog.destroy()

    def on_new(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        win = MainWindow(application=self)
        win.present()

    def do_open(self, files: List[Gio.File], file_count: int, hint: str) -> int:
        for file in files:
            self.open_in_window(file.get_uri(), window=None)
        return 0

    def open_in_window(self, uri: str, window: MainWindow = None) -> None:
        if not window or not window.document.empty:
            window = MainWindow(application=self)
        window.present()
        GLib.timeout_add(10, window.open, uri)
