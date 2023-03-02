from gi.repository import Gtk, GLib, GdkPixbuf
from ocrd_models import OcrdFile

from typing import Optional, Dict, List, Union, Callable, Any, Tuple
from itertools import count
from enum import IntEnum, auto

from ..util.image import cv_to_pixbuf, cv_scale
from ..model import Document
from ..util.config import Settings
from .icon_store import LazyLoadingListStore, RowResult

import cv2
import os

ChangeList = Union[List[str], Dict[str, str]]


class Column(IntEnum):
    PAGE_ID = 0
    TOOLTIP = auto()
    FILENAME = auto()
    URL = auto()
    THUMB = auto()
    STATE = auto()
    ORDER = auto()
    HASH = auto()


class State(IntEnum):
    MISSING = -1
    INIT = 0
    DOWNLOADING = 1
    GENERATING_THUMB = 2
    READY = 3


class PageListStore(LazyLoadingListStore):
    """
    PageListStore is a GTK.ListStore for use with GTK.IconView and works as an adapter to ocrd_browser.model.Document

    It utilizes LazyLoadingListStore for lazy thumbnail generation and
    contains the domain specific logic for handling Document events
    """

    def __init__(self, document: Document):
        """
        Initializes the underlying ListStore and fills it with a row for each page, then start the lazy loading

        The actual image and data loading happens in _load_row
        """
        columns = {
            Column.PAGE_ID: str,
            Column.TOOLTIP: str,
            Column.FILENAME: str,
            Column.URL: str,
            Column.THUMB: GdkPixbuf.Pixbuf,
            Column.STATE: int,
            Column.ORDER: int
            # Column.HASH: str (gets added by LazyLoadingListStore)
        }
        super().__init__(*(columns.values()), load_row=self._load_row, hash_row=self._hash_row)
        self.page_icons: Dict[str, GdkPixbuf.Pixbuf] = {
            icon_name: GdkPixbuf.Pixbuf.new_from_resource(
                '/org/readmachine/ocrd-browser/icons/page-{}.png'.format(icon_name)
            ) for icon_name in ['missing', 'downloading', 'generating-thumb']
        }

        # TODO end constructor here and add a new method to fill the store for testability and developer sanity
        # TODO: make file_group selectable, see https://github.com/hnesk/browse-ocrd/issues/7#issuecomment-707851109
        self.clear()
        self.document = document
        self.file_group = document.get_default_image_group(Settings.get().file_groups.preferred_images)
        self.files = document.get_image_files(self.file_group, allow_download=False)
        for page_id, file in self.files.items():
            self.add_file(page_id, file)
        GLib.timeout_add(10, self.start_loading)

    def add_file(self, page_id: str, file: Optional[OcrdFile]) -> None:
        row = [page_id, None, None, None, None, int(State.INIT), len(self)]
        row, _ = self.file_to_row(row, file)
        self.append(row)

    def file_to_row(self, row: List[Any], file: Optional[OcrdFile]) -> Tuple[List[Any], bool]:
        changed = False
        page_id = row[Column.PAGE_ID]
        if file:
            if file.local_filename:
                path = str(self.document.path(file))
                if path != row[Column.FILENAME] or row[Column.HASH] != self._hash_row(row):
                    changed = True
                    row[Column.FILENAME] = path
                    row[Column.THUMB] = self.page_icons['generating-thumb']
                    row[Column.TOOLTIP] = 'Generating Thumb {}'.format(file.local_filename)
                    row[Column.STATE] = int(State.GENERATING_THUMB)
            elif file.url:
                if file.url != row[Column.URL]:
                    changed = True
                    row[Column.URL] = file.url
                    row[Column.THUMB] = self.page_icons['downloading']
                    row[Column.TOOLTIP] = 'Downloading {}'.format(file.url)
                    row[Column.STATE] = int(State.DOWNLOADING)
        else:
            if row[Column.FILENAME] is not None or row[Column.URL] is not None:
                changed = True
            row[Column.FILENAME] = None
            row[Column.URL] = None
            row[Column.TOOLTIP] = 'No image for {}'.format(page_id)
            row[Column.THUMB] = self.page_icons['missing']
            row[Column.STATE] = int(State.MISSING)

        return row, changed

    def get_row_by_page_id(self, page_id: str) -> RowResult:
        """
        Find index and row by page_id
        """
        return self.get_row_by_column_value(Column.PAGE_ID, page_id)

    def iter_for_id(self, page_id: str) -> Optional[Gtk.TreeIter]:
        """
        Get a Gtk.TreeIter for the page_id
        """
        path = self.path_for_id(page_id)
        return self.get_iter(path) if path else None

    def path_for_id(self, page_id: str) -> Optional[Gtk.TreePath]:
        """
        Get a Gtk.TreePath for the page_id
        """
        n, row = self.get_row_by_page_id(page_id)
        return Gtk.TreePath(n) if n is not None else None

    def document_changed(self, subtype: str, changes: ChangeList) -> None:
        """
        Event callback to sync Document modifications with the ListStore

        @param subtype: str one of  'page_added', 'page_deleted', 'page_changed', 'reordered'
        @param changes: List[str] affected page_ids
        """

        def _page_added(page_ids: List[str]) -> None:
            for page_id in page_ids:
                try:
                    file = next(iter(self.document.workspace.mets.find_files(pageId=page_id, fileGrp=self.file_group.group, mimetype=self.file_group.mime)))
                    # TODO: self.document.path(file) works only for local files
                    self.add_file(page_id, file)
                except StopIteration as e:
                    raise ValueError('Page {} in group {}  not in workspace'.format(page_id, self.file_group)) from e

        def _page_deleted(page_ids: List[str]) -> None:
            for delete_page_id in reversed(page_ids):
                n, row = self.get_row_by_page_id(delete_page_id)
                self.remove(self.get_iter(Gtk.TreePath(n)))

        def _page_changed(page_ids: List[str]) -> None:
            for page_id in page_ids:
                file = None
                n, row = self.get_row_by_page_id(page_id)
                try:
                    file = next(iter(self.document.workspace.mets.find_files(pageId=page_id, fileGrp=self.file_group.group, mimetype=self.file_group.mime)))
                except StopIteration:
                    pass
                with self.handler_block(self.row_changed_handler):
                    row, changed = self.file_to_row(row, file)
                if changed:
                    path = self.path_for_id(page_id)
                    self.emit('row-changed', path, self.get_iter(path))

        def _reordered(old_to_new_ids: Dict[str, str]) -> None:
            id_to_position: Dict[str, int] = {}
            for n, row in enumerate(self):
                id_to_position[row[Column.PAGE_ID]] = n

            positions: List[int] = list(range(0, len(old_to_new_ids)))
            for old, new in old_to_new_ids.items():
                positions[id_to_position[old]] = id_to_position[new]

            self.reorder(positions)

            # Update the order in the ListStore data, not needed for now, but might help if we have sorting
            order = count(start=0)
            for page_id in self.document.page_ids:
                n, row = self.get_row_by_page_id(page_id)
                row[Column.ORDER] = next(order)

        handler: Dict[str, Callable[[Any], None]] = {
            'page_added': _page_added,
            'page_deleted': _page_deleted,
            'page_changed': _page_changed,
            'reordered': _reordered,
        }
        handler[subtype](changes)

    def _load_row(self, row: Gtk.TreeModelRow) -> Gtk.TreeModelRow:
        page_id = row[Column.PAGE_ID]
        file = self.files[page_id]
        state = row[Column.STATE]
        if state == State.DOWNLOADING:
            if file:
                file = self.document.workspace.download_file(file)
            row[Column.FILENAME] = file.local_filename
            row[Column.THUMB] = self.page_icons['generating-thumb']
            row[Column.TOOLTIP] = 'Thumbing {}'.format(file.local_filename)
            row[Column.STATE] = int(State.GENERATING_THUMB)
        elif state == State.GENERATING_THUMB:
            filename = file.local_filename
            image = cv2.imread(filename)
            row[Column.TOOLTIP] = '{} ({}x{})'.format(filename, image.shape[1], image.shape[0])
            row[Column.THUMB] = cv_to_pixbuf(cv_scale(image, 100, None))
            row[Column.STATE] = int(State.READY)
        return row

    @staticmethod
    def _hash_row(row: Gtk.TreeModelRow) -> str:
        file = row[Column.FILENAME]
        url = row[Column.URL]
        if file is not None:
            modified_time = os.path.getmtime(file)
            return '{}:{}:{}'.format(file, modified_time, url)
        else:
            return '{}:0:{}'.format(file, url)
