from gi.repository import Gtk, Gdk, Pango, Gio, GObject

from typing import List, Callable, Optional, Any, cast

from pkg_resources import resource_filename
from ocrd_browser.model import Document
from .page_store import PageListStore, ChangeList


@Gtk.Template(filename=resource_filename(__name__, '../resources/page-list.ui'))
class PagePreviewList(Gtk.IconView):
    __gtype_name__ = "PagePreviewList"

    def __init__(self, document: Document, **kwargs: Any):
        super().__init__(**kwargs)
        self.context_menu: Gtk.Menu = Gtk.Menu()
        self.setup_ui()
        self.setup_context_menu()
        self.document: Document = document
        self.model: PageListStore = PageListStore(self.document)
        self.set_model(self.model)
        # noinspection PyTypeChecker
        self.current: Optional[Gtk.TreeIter] = None

    def setup_context_menu(self) -> None:
        menu = Gio.Menu()
        action_menu = Gio.Menu()
        action_menu.append('Remove', 'win.page_remove')
        menu.append_section(None, action_menu)
        prop_menu = Gio.Menu()
        prop_menu.append('Properties', 'win.page_properties')
        menu.append_section(None, prop_menu)
        self.context_menu.bind_model(menu, None, True)
        self.context_menu.attach_to_widget(self)
        self.context_menu.show_all()

    def set_document(self, document: Document) -> None:
        self.document = document
        self.model = PageListStore(self.document)
        self.set_model(self.model)

    def document_changed(self, subtype: str, page_ids: ChangeList) -> None:
        self.model.document_changed(subtype, page_ids)
        if subtype == 'page_added' and page_ids:
            self.scroll_to_id(cast(List[str], page_ids)[-1])

    def setup_ui(self) -> None:
        self.set_text_column(PageListStore.COLUMN_PAGE_ID)
        self.set_tooltip_column(PageListStore.COLUMN_TOOLTIP)
        self.set_pixbuf_column(PageListStore.COLUMN_THUMB)
        text_renderers = [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)]
        text_renderer: Gtk.CellRendererText = text_renderers[0]
        text_renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.connect('button-press-event', self.button_pressed)

    def button_pressed(self, _sender: Gtk.Widget, event: Gdk.EventButton) -> None:
        if event.button == Gdk.BUTTON_SECONDARY and event.type == Gdk.EventType.BUTTON_PRESS:
            result = self.get_item_at_pos(*event.get_coords())
            if result:
                self.emit('on_context_menu', event, result[0], result[1])

    @GObject.Signal(arg_types=[object, object, object])
    def on_context_menu(self, event: Gdk.EventButton, path: Gtk.TreePath, _renderer: Gtk.CellRenderer) -> None:
        if len(self.get_selected_items()) <= 1:
            self.set_cursor(path, None, False)
            self.emit('select_cursor_item')
        self.context_menu.popup_at_pointer(event)

    def get_selected_ids(self) -> List[str]:
        return [self.model[path][PageListStore.COLUMN_PAGE_ID] for path in self.get_selected_items()]

    def goto_index(self, index: int) -> None:
        index = index if index >= 0 else len(self.model) + index
        if 0 <= index < len(self.model):
            self.goto_path(Gtk.TreePath(index))

    def scroll_to_id(self, page_id: str) -> None:
        path = self.model.path_for_id(page_id)
        if path:
            self.scroll_to_path(path, False, 0, 1.0)

    def skip(self, pos: int) -> None:
        if not self.current:
            self.current = self.model.get_iter(Gtk.TreePath(0))
        iterate: Callable[[Gtk.TreeIter], Gtk.TreeIter] = self.model.iter_previous if pos < 0 else self.model.iter_next
        n = self.current
        for _ in range(0, abs(pos)):
            n = iterate(n)
        self.goto_path(self.model.get_path(n))

    def goto_path(self, path: Gtk.TreePath) -> None:
        self.set_cursor(path, None, False)
        self.emit('select_cursor_item')
        self.emit('activate_cursor_item')
        self.grab_focus()

    def do_selection_changed(self) -> None:
        self.emit('pages_selected', self.get_selected_ids())

    def do_item_activated(self, path: Gtk.TreePath) -> None:
        self.current = self.model.get_iter(path)
        self.emit('page_activated', self.model[path][PageListStore.COLUMN_PAGE_ID])

    @GObject.Signal()
    def page_activated(self, page_id: str) -> None:
        pass

    @GObject.Signal(arg_types=[object])
    def pages_selected(self, page_ids: List[str]) -> None:
        pass
