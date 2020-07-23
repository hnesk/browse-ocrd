import gi

from ocrd_browser.icon_store import PagePreviewList

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, Gio, GObject, GLib

from ocrd_browser import __version__
from ocrd_browser.model import Document
from ocrd_browser.views import ViewManager, ViewImages, View


class ActionRegistry:
    def __init__(self):
        self.actions = {}

    def create_simple_action(self, name, callback=None):
        callback = callback if callback else getattr(self, 'on_' + name)
        action: Gio.SimpleAction = Gio.SimpleAction.new(name)
        action.connect("activate", callback)
        self.add_action(action)
        self.actions[name] = action
        return action


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/main-window.ui")
class MainWindow(Gtk.ApplicationWindow, ActionRegistry):
    __gtype_name__ = "MainWindow"

    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    page_list_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()
    panes: Gtk.Paned = Gtk.Template.Child()
    current_page_label: Gtk.Label = Gtk.Template.Child()
    view_container: Gtk.Box = Gtk.Template.Child()
    create_view_select: Gtk.ComboBoxText = Gtk.Template.Child()

    def __init__(self, file=None, **kwargs):
        Gtk.ApplicationWindow.__init__(self, **kwargs)
        ActionRegistry.__init__(self)
        self.views = []
        self.current_page_id = None
        self.create_simple_action('close')
        self.create_simple_action('goto_first')
        self.create_simple_action('go_back')
        self.create_simple_action('go_forward')
        self.create_simple_action('goto_last')
        self.create_simple_action('create_view')

        close_view_action = Gio.SimpleAction.new("close_view", GLib.Variant("s", "").get_type())
        close_view_action.connect("activate", self.on_close_view)
        self.add_action(close_view_action)

        self.document = Document.load(file)

        title = self.document.workspace.mets.unique_identifier if self.document.workspace.mets.unique_identifier else '<unnamed>'

        self.set_title(title)
        self.header_bar.set_title(title)
        self.header_bar.set_subtitle(self.document.workspace.directory)

        self.page_list = PagePreviewList(self.document)
        self.page_list_scroller.add(self.page_list)
        self.page_list.connect('page_selected', self.page_selected)

        for id_, view in self.view_manager.get_view_options().items():
            self.create_view_select.append(id_, view)
        self.add_view(ViewImages(document=self.document))

        if len(self.document.page_ids):
            self.page_selected(None, self.document.page_ids[0])

    @property
    def view_manager(self) -> ViewManager:
        return self.get_application().view_manager

    def add_view(self, view: 'View'):
        view.set_document(self.document)
        view.set_name('view_{}'.format(len(self.views)))
        view.setup()
        self.views.append(view)
        self.connect('page_activated', view.page_activated)
        self.view_container.pack_start(view, True, True, 3)

    def page_selected(self, _, page_id):
        if self.current_page_id != page_id:
            self.current_page_id = page_id
            self.emit('page_activated', page_id)

    @GObject.Signal(arg_types=(str,))
    def page_activated(self, page_id):
        index = self.document.page_ids.index(page_id)
        self.current_page_label.set_text('#{} ({}/{})'.format(page_id, index + 1, len(self.document.page_ids)))
        self.update_ui()
        pass

    def update_ui(self):
        if self.current_page_id and len(self.document.page_ids) > 0:
            index = self.document.page_ids.index(self.current_page_id)
            last_page = len(self.document.page_ids) - 1
            self.actions['goto_first'].set_enabled(index > 0)
            self.actions['go_back'].set_enabled(index > 0)
            self.actions['go_forward'].set_enabled(index < last_page)
            self.actions['goto_last'].set_enabled(index < last_page)

    def on_close(self, _a: Gio.SimpleAction, _p):
        self.destroy()

    def on_goto_first(self, _a: Gio.SimpleAction, _p):
        self.page_list.goto_index(0)

    def on_go_forward(self, _a: Gio.SimpleAction, _p):
        self.page_list.skip(1)

    def on_go_back(self, _a: Gio.SimpleAction, _p):
        self.page_list.skip(-1)

    def on_goto_last(self, _a: Gio.SimpleAction, _p):
        self.page_list.goto_index(-1)

    def on_create_view(self, _a: Gio.SimpleAction, _):
        active_id = self.create_view_select.get_active_id()
        view = self.view_manager.get_view(active_id)
        if view:
            self.add_view(view(document=self.document))

    def on_close_view(self, _action: Gio.SimpleAction, view_name: GLib.Variant):
        for view in self.views:
            if view.get_name() == view_name.get_string():
                view.destroy()


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/about-dialog.ui")
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self, **kwargs):
        Gtk.AboutDialog.__init__(self, **kwargs)
        self.set_logo(GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/logo.png'))
        self.set_version(__version__)


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/open-dialog.ui")
class OpenDialog(Gtk.FileChooserDialog):
    __gtype_name__ = "OpenDialog"

    def __init__(self, **kwargs):
        Gtk.FileChooserDialog.__init__(self, **kwargs)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("METS files")
        filter_text.add_mime_type("text/xml")
        self.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        self.add_filter(filter_any)
