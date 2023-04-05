from gi.repository import Gio, Gtk, GLib, Gdk

from typing import List, Dict, Any

from ocrd_browser import __version__
from ocrd_browser.util.gtk import ActionRegistry
from ocrd_browser.ui import MainWindow, WindowFlags, AboutDialog, OpenDialog
from ocrd_browser.view import ViewRegistry

from importlib_metadata import entry_points


class OcrdBrowserApplication(Gtk.Application):
    # TODO: Parse arguments (with Gtk or click) to open certain views by mets+page_id+view(view_configuration_dict) and deep filename e.g.
    # OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP/OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP_0001.xml ->
    # file_grp => OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP /     <mets:fileGrp USE="OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP"><mets:file MIMETYPE="application/vnd.prima.page+xml" ID="OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP_0001"><mets:FLocat LOCTYPE="OTHER" OTHERLOCTYPE="FILE" xlink:href="OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP/OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP_0001.xml"/></mets:file>
    # mimetype => application/vnd.prima.page+xml
    # FILEID => OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP_0001 /  <mets:fptr FILEID="OCR-D-OCR-TESS-frk-SEG-LINE-tesseract-ocropy-DEWARP_0001"/>
    # page.id => PHYS_0017 / <mets:div TYPE="page" ID="PHYS_0017">
    # mets.xml + page.id + view_by_mimetype(mimetype)(file_grp = (file_grp,mimetype))
    # TODO: Test application startup for all kinds of mets.xml (not necessarily OCR-D mets.xml) and views without crashes
    def __init__(self) -> None:
        Gtk.Application.__init__(self, application_id='org.readmachine.ocrd-browser',
                                 flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.actions = ActionRegistry(for_widget=self)
        self.view_registry = ViewRegistry.create_from_entry_points()

        self.window_flags = WindowFlags.NONE
        self.readonly = False

        self.add_main_option("version", ord("v"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Show version and exit", None)
        self.add_main_option("maximize", ord("m"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Open in maximized window", None)
        self.add_main_option("fullscreen", ord("f"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Open in fullscreen window", None)
        self.add_main_option("readonly", ord("r"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Open restricted (no edit/open functionality)", None)

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self.actions.create('new')
        self.actions.create('open')
        self.actions.create('about')
        self.actions.create('quit')

        self.set_accels_for_action('view.zoom_by(1)', ['<Ctrl>plus'])
        self.set_accels_for_action('view.zoom_by(-1)', ['<Ctrl>minus'])
        self.set_accels_for_action('view.zoom_to::original', ['<Ctrl>0'])
        self.set_accels_for_action('view.zoom_to::width', ['<Ctrl>numbersign'])
        self.set_accels_for_action('view.zoom_to::page', ['<Ctrl><Alt>numbersign'])
        self.set_accels_for_action("win.fullscreen", ['F11'])

        for entry_point in entry_points(group='ocrd_browser_ext'):
            (entry_point.load())(self)

        self.load_css()

    def load_css(self) -> None:
        css = Gtk.CssProvider()
        css.load_from_resource('/org/readmachine/ocrd-browser/css/theme.css')
        # noinspection PyArgumentList
        Gtk.StyleContext().add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        # css = Gtk.CssProvider()
        # css.load_from_path('/home/jk/PycharmProjects/ocrd-browser/gresources/css/test.css')
        # Gtk.StyleContext().add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def do_activate(self) -> None:
        self._present_window(self.get_active_window())

    def on_about(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        about_dialog = AboutDialog(application=self, transient_for=self.get_active_window(), modal=True)
        about_dialog.present()

    def on_quit(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        open_windows: int = 0
        window: MainWindow
        for window in self.get_windows():
            if isinstance(window, MainWindow) and window.close_confirm():
                window.destroy()
            else:
                open_windows += 1
        if open_windows == 0:
            self.quit()

    def on_open(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        open_dialog = OpenDialog(application=self, transient_for=self.get_active_window(), modal=True)
        response = open_dialog.run()
        if response == Gtk.ResponseType.OK:
            self.open_in_window(open_dialog.get_uri(), window=open_dialog.get_transient_for())
        open_dialog.destroy()

    def on_new(self, _action: Gio.SimpleAction, _param: str = None) -> None:
        win = MainWindow(application=self, readonly=self.readonly)
        win.present()

    def do_open(self, files: List[Gio.File], file_count: int, hint: str) -> int:
        for file in files:
            self.open_in_window(file.get_uri(), window=None)
        return 0

    def do_handle_local_options(self, goptions: GLib.VariantDict) -> int:
        options: Dict[str, Any] = goptions.end().unpack()
        if options.get('version', False):
            print('browse-ocrd: {}'.format(__version__))
            return 0
        if options.get('maximize', False):
            self.window_flags |= WindowFlags.MAXIMIZE
        if options.get('fullscreen', False):
            self.window_flags |= WindowFlags.FULLSCREEN
        if options.get('readonly', False):
            self.readonly = True

        return -1

    def open_in_window(self, uri: str, window: MainWindow = None) -> None:
        if not window or not window.document.empty:
            window = MainWindow(application=self, readonly=self.readonly)
        self._present_window(window)
        GLib.timeout_add(10, window.open, uri)

    def _present_window(self, win: MainWindow) -> None:
        if not win:
            win = MainWindow(application=self, readonly=self.readonly)
        if self.window_flags & WindowFlags.MAXIMIZE:
            win.maximize()
        if self.window_flags & WindowFlags.FULLSCREEN:
            win.fullscreen()

        win.present()
