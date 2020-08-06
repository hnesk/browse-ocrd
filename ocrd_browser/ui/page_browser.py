from pathlib import Path

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib, Gio, GObject
from pkg_resources import resource_filename
from typing import List, Optional, Dict
from itertools import count
from ocrd_browser.util.image import cv_scale, cv_to_pixbuf
from ocrd_browser.model import Document, DEFAULT_FILE_GROUP
from . import LazyLoadingListStore

import cv2
import os


@Gtk.Template(filename=resource_filename(__name__, '../resources/page-list.ui'))
class PagePreviewList(Gtk.IconView):
    __gtype_name__ = "PagePreviewList"

    def __init__(self, document: Document, **kwargs):
        super().__init__(**kwargs)
        self.document: Document = None
        self.current: Gtk.TreeIter = None
        self.model: LazyLoadingListStore = None
        self.loading_image_pixbuf: GdkPixbuf.Pixbuf = None
        self.context_menu: Gtk.Menu = None
        self.setup_ui()
        self.setup_context_menu()
        self.set_document(document)

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
        self.setup_model()

    def document_changed(self, subtype: str, page_ids: List[str]):
        def _document_page_added(page_ids: List[str]):
            page_id = None
            for page_id in page_ids:
                file = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=page_id)[0]
                file_name = str(self.document.path(file.local_filename))
                self.model.append((page_id, '', file_name, None, len(self.model)))
            if page_id is not None:
                self.scroll_to_id(page_id)

        def _document_page_deleted(page_ids: List[str]):
            for delete_page_id in reversed(page_ids):
                n, row = self.model.get_row_by_column_value(0, delete_page_id)
                self.model.remove(self.model.get_iter(Gtk.TreePath(n)))

        def _document_page_changed(page_ids: List[str]):
            for page_id in page_ids:
                n, row = self.model.get_row_by_column_value(0, page_id)
                files = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=page_id)
                if files:
                    file_name = str(self.document.path(files[0]))
                    row[2] = file_name

        def _document_reordered(_page_ids: List[str]):
            order = count(start=1)
            for page_id in self.document.page_ids:
                n, row = self.model.get_row_by_column_value(0, page_id)
                row[4] = next(order)

        handler = {
            'page_added': _document_page_added,
            'page_deleted': _document_page_deleted,
            'page_changed': _document_page_changed,
            'reordered': _document_reordered,
        }
        handler[subtype](page_ids)


    def setup_ui(self):
        self.loading_image_pixbuf = GdkPixbuf.Pixbuf.new_from_resource(
            '/org/readmachine/ocrd-browser/icons/loading.png')
        self.set_text_column(0)
        self.set_tooltip_column(1)
        self.set_pixbuf_column(3)
        text_renderer: Gtk.CellRendererText = \
            [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)][0]
        text_renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.connect('button-release-event', self.button_pressed)

    def button_pressed(self, _sender, event: Gdk.EventButton):
        if event.get_button()[1] == 3:
            path, renderer = self.get_item_at_pos(*event.get_coords())
            row = self.model[path]
            self.emit('on_context_menu', event, row, path, renderer)

    @GObject.Signal(arg_types=(object, object, object, object))
    def on_context_menu(self, event: Gdk.EventButton, row: Gtk.TreeModelRow, path: Gtk.TreePath,
                        renderer: Gtk.CellRenderer):
        if len(self.get_selected_items()) <= 1:
            self.set_cursor(path, None, False)
            self.emit('select_cursor_item')
        self.context_menu.popup_at_pointer(event)

    def setup_model(self):
        file_lookup = self.get_image_paths(self.document)
        self.model = LazyLoadingListStore(str, str, str, GdkPixbuf.Pixbuf, int,
                                          init_row=self.init_row, load_row=self.load_row, hash_row=self.hash_row)
        order = count(start=1)
        for page_id in self.document.page_ids:
            file = str(file_lookup[page_id])
            self.model.append((page_id, '', file, None, next(order)))
        self.set_model(self.model)
        self.model.set_sort_column_id(4, Gtk.SortType.ASCENDING)
        GLib.timeout_add(10, self.model.start_loading)

    def init_row(self, row: Gtk.TreeModelRow):
        row[1] = 'Loading {}'.format(row[2])
        row[3] = self.loading_image_pixbuf

    @staticmethod
    def load_row(row):
        image = cv2.imread(row[2])
        row[1] = '{} ({}x{})'.format(row[2], image.shape[1], image.shape[0])
        row[3] = cv_to_pixbuf(cv_scale(image, 100, None))
        return row

    @staticmethod
    def hash_row(row: Gtk.TreeModelRow):
        file = row[2]
        mtime = os.path.getmtime(file)
        return '{}:{}'.format(file, mtime)

    @staticmethod
    def get_image_paths(document: Document, file_group='OCR-D-IMG') -> Dict[str, Path]:
        images = document.workspace.mets.find_files(fileGrp=file_group)
        page_ids = document.workspace.mets.get_physical_pages(for_fileIds=[image.ID for image in images])
        file_paths = [document.path(image.url) for image in images]
        return dict(zip(page_ids, file_paths))

    def get_selected_ids(self):
        return [self.model[path][0] for path in self.get_selected_items()]

    def goto_index(self, index):
        index = index if index >= 0 else len(self.model) + index
        if 0 <= index < len(self.model):
            self.goto_path(Gtk.TreePath(index))

    def path_for_id(self, page_id):
        n, row = self.model.get_row_by_column_value(0, page_id)
        return Gtk.TreePath(n) if n is not None else None

    def scroll_to_id(self, page_id):
        path = self.path_for_id(page_id)
        self.scroll_to_path(path, False, 0, 1.0)

    def skip(self, pos):
        if not self.current:
            self.current = self.model.get_iter(Gtk.TreePath(0))
        iterate = self.model.iter_previous if pos < 0 else self.model.iter_next
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

    @GObject.Signal(arg_types=(object,))
    def pages_selected(self, page_ids: List[str]):
        print(page_ids)
        pass
