from gi.repository import Gtk, GdkPixbuf, Gio, GObject, GLib, Gdk
from ocrd_models import OcrdFile

from ocrd_browser.model import Document
from ocrd_browser.view import ViewRegistry, ViewPage
from ocrd_browser.util.gtk import ActionRegistry
from .dialogs import SaveDialog, SaveChangesDialog
from .page_browser import PagePreviewList
from pkg_resources import resource_filename
from typing import List, cast, Any, Optional

from ..view.manager import ViewManager


@Gtk.Template(filename=resource_filename(__name__, '../resources/main-window.ui'))
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    page_list_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()
    panes: Gtk.Paned = Gtk.Template.Child()
    current_page_label: Gtk.Label = Gtk.Template.Child()
    view_container: Gtk.Box = Gtk.Template.Child()
    view_menu_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs: Any):
        Gtk.ApplicationWindow.__init__(self, **kwargs)
        # noinspection PyCallByClass,PyArgumentList
        self.set_icon(GdkPixbuf.Pixbuf.new_from_resource("/org/readmachine/ocrd-browser/icons/icon.png"))
        self.view_manager = ViewManager(self, self.view_container)
        self.current_page_id: Optional[str] = None
        # noinspection PyTypeChecker
        self.document = Document.create(emitter=self.emit)

        self.actions = ActionRegistry(for_widget=self)
        self.actions.create('close')
        self.actions.create('goto_first')
        self.actions.create('go_back')
        self.actions.create('go_forward')
        self.actions.create('goto_last')
        self.actions.create('page_remove')
        self.actions.create('page_properties')
        self.actions.create('close_view', param_type=GLib.VariantType("s"))
        self.actions.create('split_view', param_type=GLib.VariantType("(ssb)"))
        self.actions.create('create_view', param_type=GLib.VariantType("s"))
        self.actions.create('replace_view', param_type=GLib.VariantType("(ss)"))
        self.actions.create('toggle_edit_mode', state=GLib.Variant('b', False))
        self.actions.create('save')
        self.actions.create('save_as')

        self.connect('delete-event', self.on_delete_event)

        self.page_list = PagePreviewList(self.document)
        self.page_list_scroller.add(self.page_list)
        self.page_list.connect('page_activated', self.on_page_activated)
        self.page_list.connect('pages_selected', self.on_pages_selected)

        for id_, view in self.view_registry.get_view_options().items():
            menu_item = Gtk.ModelButton(visible=True, centered=False, halign=Gtk.Align.FILL, label=view, hexpand=True)
            menu_item.set_detailed_action_name('win.create_view("{}")'.format(id_))
            self.view_menu_box.pack_start(menu_item, True, True, 0)

        self.view_manager.set_root_view(ViewPage)
        # self.view_manager.split(None, ViewPage, False)

        self.update_ui()

    def on_page_remove(self, _a: Gio.SimpleAction, _p: None) -> None:
        for page_id in self.page_list.get_selected_ids():
            self.document.delete_page(page_id)

    def on_page_properties(self, _a: Gio.SimpleAction, _p: None) -> None:
        pass

    @Gtk.Template.Callback()
    def on_recent_menu_item_activated(self, recent_chooser: Gtk.RecentChooserMenu) -> None:
        app = self.get_application()
        item: Gtk.RecentInfo = recent_chooser.get_current_item()
        app.open_in_window(item.get_uri(), window=self)

    def open(self, uri: str) -> None:
        self.set_title('Loading')
        self.header_bar.set_title('Loading ...')
        self.header_bar.set_subtitle(uri)
        self.update_ui()
        # Give GTK some break to show the Loading message
        GLib.timeout_add(50, self._open, uri)

    def _open(self, uri: str) -> None:
        # noinspection PyTypeChecker
        self.document = Document.load(uri, emitter=self.emit)
        self.page_list.set_document(self.document)

        self.view_manager.set_document(self.document)
        self.update_ui()

        if len(self.document.page_ids):
            self.on_page_activated(None, self.document.page_ids[0])

    @property
    def view_registry(self) -> ViewRegistry:
        return cast(MainWindow, self.get_application()).view_registry

    def on_page_activated(self, _sender: Optional[Gtk.Widget], page_id: str) -> None:
        if self.current_page_id != page_id:
            self.current_page_id = page_id
            self.emit('page_activated', page_id)

    @GObject.Signal(arg_types=[str])
    def page_activated(self, page_id: str) -> None:
        index = self.document.page_ids.index(page_id)
        self.current_page_label.set_text('{}/{}'.format(index + 1, len(self.document.page_ids)))
        self.update_ui()

    def on_pages_selected(self, _sender: Optional[Gtk.Widget], page_ids: List[str]) -> None:
        self.emit('pages_selected', page_ids)

    @GObject.Signal(arg_types=[object])
    def pages_selected(self, page_ids: List[str]) -> None:
        pass

    @GObject.Signal(arg_types=[str, object])
    def document_changed(self, subtype: str, page_ids: List[str]) -> None:
        self.page_list.document_changed(subtype, page_ids)
        self.update_ui()

    @GObject.Signal(arg_types=[object])
    def document_saved(self, _saved: Document) -> None:
        self.update_ui()

    @GObject.Signal(arg_types=[float, object])
    def document_saving(self, progress: float, file: Optional[OcrdFile]) -> None:
        pass

    def update_ui(self) -> None:
        title = self.document.title + (' *' if self.document.modified else '')
        self.set_title(title)
        self.header_bar.set_title(title)
        self.header_bar.set_subtitle(self.document.original_url)

        can_go_back = False
        can_go_forward = False
        if self.current_page_id and self.current_page_id in self.document.page_ids:
            index = self.document.page_ids.index(self.current_page_id)
            last_page = len(self.document.page_ids) - 1
            can_go_back = index > 0
            can_go_forward = index < last_page

        self.actions['goto_first'].set_enabled(can_go_back)
        self.actions['go_back'].set_enabled(can_go_back)
        self.actions['go_forward'].set_enabled(can_go_forward)
        self.actions['goto_last'].set_enabled(can_go_forward)
        self.actions['page_remove'].set_enabled(self.document.editable)
        # noinspection PyCallByClass,PyArgumentList
        self.actions['toggle_edit_mode'].set_state(GLib.Variant.new_boolean(self.document.editable))
        self.actions['save'].set_enabled(self.document.modified)
        self.view_manager.update_ui()

    def close_confirm(self) -> bool:
        if self.document.modified:
            # Do you wanna save the changes?
            d = SaveChangesDialog(document=self.document, transient_for=self, modal=True)
            save_changes = d.run()
            d.destroy()

            if save_changes == Gtk.ResponseType.NO:
                return True
            elif save_changes == Gtk.ResponseType.CANCEL:
                return False
            elif save_changes == Gtk.ResponseType.YES:
                return self.on_save()
            return False
        else:
            return True

    def on_close(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        if self.close_confirm():
            self.destroy()

    def on_delete_event(self, _window: 'MainWindow', _event: Gdk.Event) -> bool:
        return not self.close_confirm()

    def on_goto_first(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.page_list.goto_index(0)

    def on_go_forward(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.page_list.skip(1)

    def on_go_back(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.page_list.skip(-1)

    def on_goto_last(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.page_list.goto_index(-1)

    def on_create_view(self, _a: Gio.SimpleAction, selected_view_id: GLib.Variant) -> None:
        view_class = self.view_registry.get_view(selected_view_id.get_string())
        self.view_manager.add(view_class)

    def on_replace_view(self, _a: Gio.SimpleAction, arguments: GLib.Variant) -> None:
        (replace_view, new_view_name) = arguments
        new_view_type = self.view_registry.get_view(new_view_name)
        self.view_manager.replace(replace_view, new_view_type)

    def on_close_view(self, _action: Gio.SimpleAction, view_name: GLib.Variant) -> None:
        try:
            self.view_manager.close(view_name.get_string())
        except ValueError:
            # Tried to remove last view
            pass

    def on_split_view(self, _action: Gio.SimpleAction, arguments: GLib.Variant) -> None:
        (split_view, new_view_name, horizontal) = arguments
        new_view_type = self.view_registry.get_view(new_view_name)
        self.view_manager.split(split_view, new_view_type, horizontal)

    def on_save(self, _a: Gio.SimpleAction = None, _p: None = None) -> bool:
        if self.document.original_url:
            return self.save()
        else:
            return self.save_as()

    def on_save_as(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.save_as()

    def save(self) -> bool:
        self.document.save()
        self.update_ui()
        return True

    def save_as(self) -> bool:
        save_dialog = SaveDialog(application=self.get_application(), transient_for=self, modal=True)
        if self.document.original_url:
            save_dialog.set_filename(self.document.original_url)
        else:
            save_dialog.set_current_name('mets.xml')
        response = save_dialog.run()
        should_save = bool(response == Gtk.ResponseType.OK)
        if should_save:
            self.document.save_as(save_dialog.get_uri())
        save_dialog.destroy()
        self.update_ui()
        return should_save

    def on_toggle_edit_mode(self, _a: Gio.SimpleAction = None, _p: None = None) -> None:
        self.document.editable = not self.document.editable
        self.update_ui()
