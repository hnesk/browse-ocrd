import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio,  Gtk
from typing import List
from ocrd_browser.window import MainWindow, AboutDialog, OpenDialog, ActionRegistry


class OcrdBrowserApplication(Gtk.Application, ActionRegistry):
    def __init__(self):
        Gtk.Application.__init__(self, application_id='org.readmachine.ocrd-browser', flags=Gio.ApplicationFlags.HANDLES_OPEN)
        ActionRegistry.__init__(self)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.create_simple_action('new')
        self.create_simple_action('open')
        self.create_simple_action('about')
        self.create_simple_action('quit')

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = MainWindow(application=self)
        win.present()

    def on_about(self, action, param):
        about_dialog = AboutDialog(application=self, transient_for = self.get_active_window(), modal = True)
        about_dialog.present()

    def on_quit(self, action, param):
        self.quit()

    def on_open(self, action, param):
        open_dialog = OpenDialog(application=self, transient_for = self.get_active_window(), modal = True)
        open_dialog.set_current_folder('/home/jk/Projekte/ocrd-venv/projects/')

        response = open_dialog.run()
        if response == Gtk.ResponseType.OK:
            win = MainWindow(application=self, file=open_dialog.get_filename())
            win.present()

        open_dialog.destroy()

    def on_new(self, action, param):
        win = MainWindow(application=self)
        win.present()

    def do_open(self, files: List[Gio.File], file_count: int, hint: str):
        for file in files:
            win = MainWindow(application=self, file=file.get_path())
            win.present()

        return 0


