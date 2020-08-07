from gi.repository import Gtk, GdkPixbuf, Gio, GObject, GLib

from ocrd_browser.model import Document, DEFAULT_FILE_GROUP
from ocrd_browser.view import ViewRegistry, View, ViewImages
from ocrd_browser.util.gtk import ActionRegistry
from .page_browser import PagePreviewList
from pkg_resources import resource_filename
from typing import List, cast


@Gtk.Template(filename=resource_filename(__name__, '../resources/main-window.ui'))
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    page_list_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()
    panes: Gtk.Paned = Gtk.Template.Child()
    current_page_label: Gtk.Label = Gtk.Template.Child()
    view_container: Gtk.Box = Gtk.Template.Child()
    view_menu_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        Gtk.ApplicationWindow.__init__(self, **kwargs)
        self.set_icon(GdkPixbuf.Pixbuf.new_from_resource("/org/readmachine/ocrd-browser/icons/icon.png"))
        self.views = []
        self.current_page_id = None
        self.document = Document.create(emitter=self.emit)

        vstring = GLib.Variant("s", "")

        self.actions = ActionRegistry(for_widget=self)
        self.actions.create('close')
        self.actions.create('goto_first')
        self.actions.create('go_back')
        self.actions.create('go_forward')
        self.actions.create('goto_last')
        self.actions.create('page_remove')
        self.actions.create('page_properties')
        self.actions.create('close_view', param_type=vstring)
        self.actions.create('create_view', param_type=vstring)

        self.page_list = PagePreviewList(self.document)
        self.page_list_scroller.add(self.page_list)
        self.page_list.connect('page_activated', self.on_page_activated)

        for id_, view in self.view_registry.get_view_options().items():
            menu_item = Gtk.ModelButton(visible=True, centered=False, halign=Gtk.Align.FILL, label=view, hexpand=True)
            menu_item.set_detailed_action_name('win.create_view("{}")'.format(id_))
            self.view_menu_box.pack_start(menu_item, True, True, 0)

        self.add_view(ViewImages)

        self.update_ui()

    def on_page_remove(self, _a: Gio.SimpleAction, _p):
        for page_id in self.page_list.get_selected_ids():
            self.document.delete_page(page_id)

    def on_page_properties(self, _a: Gio.SimpleAction, _p):
        print(self.page_list.get_selected_items())

    @Gtk.Template.Callback()
    def on_recent_menu_item_activated(self, recent_chooser: Gtk.RecentChooserMenu):
        app = self.get_application()
        item: Gtk.RecentInfo = recent_chooser.get_current_item()
        app.open_in_window(item.get_uri(), window=self)

    def open(self, uri):
        self.set_title('Loading')
        self.header_bar.set_title('Loading ...')
        self.header_bar.set_subtitle(uri)
        self.update_ui()
        # Give GTK some break to show the Loading message
        GLib.timeout_add(50, self._open, uri)

    def _open(self, uri):
        self.document = Document.load(uri, emitter=self.emit)
        self.page_list.set_document(self.document)

        title = self.document.workspace.mets.unique_identifier if self.document.workspace.mets.unique_identifier else '<unnamed>'
        self.set_title(title)
        self.header_bar.set_title(title)
        self.header_bar.set_subtitle(self.document.workspace.directory)

        for view in self.views:
            view.set_document(self.document)

        if len(self.document.page_ids):
            self.on_page_activated(None, self.document.page_ids[0])

    @property
    def view_registry(self) -> ViewRegistry:
        return cast(MainWindow, self.get_application()).view_registry

    def add_view(self, view_class):
        name = 'view_{}'.format(len(self.views))
        view: View = view_class(name, self)
        view.build()
        view.set_document(self.document)
        self.views.append(view)
        self.connect('page_activated', view.page_activated)
        self.page_list.connect('pages_selected', view.pages_selected)
        self.view_container.pack_start(view.container, True, True, 3)

    def on_page_activated(self, _, page_id):
        if self.current_page_id != page_id:
            self.current_page_id = page_id
            self.emit('page_activated', page_id)

    @GObject.Signal(arg_types=(str,))
    def page_activated(self, page_id):
        index = self.document.page_ids.index(page_id)
        self.current_page_label.set_text('{}/{}'.format(index + 1, len(self.document.page_ids)))
        self.update_ui()
        pass

    @GObject.Signal(arg_types=(str, object,))
    def document_changed(self, subtype: str, page_ids: List[str]):
        self.page_list.document_changed(subtype, page_ids)

    @GObject.Signal()
    def document_saved(self):
        print('saved')

    def update_ui(self):
        can_go_back = False
        can_go_forward = False
        if self.current_page_id and len(self.document.page_ids) > 0:
            index = self.document.page_ids.index(self.current_page_id)
            last_page = len(self.document.page_ids) - 1
            can_go_back = index > 0
            can_go_forward = index < last_page

        self.actions['goto_first'].set_enabled(can_go_back)
        self.actions['go_back'].set_enabled(can_go_back)
        self.actions['go_forward'].set_enabled(can_go_forward)
        self.actions['goto_last'].set_enabled(can_go_forward)

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
        return 1

    def on_create_view(self, _a, selected_view_id: GLib.Variant):
        view_class = self.view_registry.get_view(selected_view_id.get_string())
        if view_class:
            self.add_view(view_class)

    def on_close_view(self, _action: Gio.SimpleAction, view_name: GLib.Variant):
        for view in self.views:
            if view.name == view_name.get_string():
                view.container.destroy()
                break
        self.disconnect_by_func(view.page_activated)
        self.views.remove(view)
        del view
