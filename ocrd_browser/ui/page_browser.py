from gi.repository import Gtk, Gdk, Pango, Gio, GObject
from pkg_resources import resource_filename
from typing import List, Callable, Optional
from ocrd_browser.model import Document
from .page_store import PageListStore


@Gtk.Template(filename=resource_filename(__name__, '../resources/page-list.ui'))
class PagePreviewList(Gtk.IconView):
    __gtype_name__ = "PagePreviewList"

    def __init__(self, document: Document, **kwargs):
        super().__init__(**kwargs)
        self.context_menu: Optional[Gtk.Menu] = None
        self.setup_ui()
        self.setup_context_menu()
        self.document: Document = document
        self.model: PageListStore = PageListStore(self.document)
        self.set_model(self.model)
        # noinspection PyTypeChecker
        self.current: Optional[Gtk.TreeIter] = None

    def setup_context_menu(self):
        menu = Gio.Menu()
        action_menu = Gio.Menu()
        action_menu.append('Remove', 'win.page_remove')
        menu.append_section(None, action_menu)
        prop_menu = Gio.Menu()
        prop_menu.append('Properties', 'win.page_properties')
        menu.append_section(None, prop_menu)
        self.context_menu: Gtk.Menu = Gtk.Menu()
        self.context_menu.bind_model(menu, None, True)
        self.context_menu.attach_to_widget(self)
        self.context_menu.show_all()

    def set_document(self, document):
        self.document = document
        self.model = PageListStore(self.document)
        self.set_model(self.model)

    def document_changed(self, subtype: str, page_ids: List[str]):
        self.model.document_changed(subtype, page_ids)
        if subtype == 'page_added' and page_ids:
            self.scroll_to_id(page_ids[-1])

    def setup_ui(self):
        self.set_text_column(0)
        self.set_tooltip_column(1)
        self.set_pixbuf_column(3)
        text_renderers = [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)]
        text_renderer: Gtk.CellRendererText = text_renderers[0]
        text_renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.connect('button-release-event', self.button_pressed)

    def button_pressed(self, _sender, event: Gdk.EventButton):
        if event.get_button()[1] == 3:
            path, renderer = self.get_item_at_pos(*event.get_coords())
            self.emit('on_context_menu', event, path, renderer)

    @GObject.Signal(arg_types=[object, object, object, object])
    def on_context_menu(self, event: Gdk.EventButton, path: Gtk.TreePath, _renderer: Gtk.CellRenderer):
        if len(self.get_selected_items()) <= 1:
            self.set_cursor(path, None, False)
            self.emit('select_cursor_item')
        self.context_menu.popup_at_pointer(event)

    def get_selected_ids(self):
        return [self.model[path][0] for path in self.get_selected_items()]

    def goto_index(self, index):
        index = index if index >= 0 else len(self.model) + index
        if 0 <= index < len(self.model):
            self.goto_path(Gtk.TreePath(index))

    def scroll_to_id(self, page_id):
        path = self.model.path_for_id(page_id)
        if path:
            self.scroll_to_path(path, False, 0, 1.0)

    def skip(self, pos):
        if not self.current:
            self.current = self.model.get_iter(Gtk.TreePath(0))
        iterate: Callable = self.model.iter_previous if pos < 0 else self.model.iter_next
        n = self.current
        for _ in range(0, abs(pos)):
            n = iterate(n)
        self.goto_path(self.model.get_path(n))

    def goto_path(self, path):
        self.set_cursor(path, None, False)
        self.emit('select_cursor_item')
        self.emit('activate_cursor_item')
        self.grab_focus()

    def do_selection_changed(self):
        self.emit('pages_selected', self.get_selected_ids())

    def do_item_activated(self, path: Gtk.TreePath):
        self.current = self.model.get_iter(path)
        self.emit('page_activated', self.model[path][0])

    @GObject.Signal()
    def page_activated(self, page_id: str):
        pass

    @GObject.Signal(arg_types=[object])
    def pages_selected(self, page_ids: List[str]):
        print(page_ids)
        pass
