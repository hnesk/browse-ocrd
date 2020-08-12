from gi.repository import Gtk, GLib, GdkPixbuf

from typing import Tuple, Optional, Dict, List, Union
from itertools import count
from pathlib import Path

from ocrd_browser.util.image import cv_to_pixbuf, cv_scale
from ocrd_browser.model import Document, DEFAULT_FILE_GROUP
from .icon_store import LazyLoadingListStore

import cv2
import os

RowResult = Tuple[Optional[int], Optional[Gtk.TreeModelRow]]


class PageListStore(LazyLoadingListStore):
    """
    PageListStore is a GTK.ListStore for use with GTK.IconView and works as an adapter to ocrd_browser.model.Document

    It utilizes LazyLoadingListStore for lazy thumbnail generation and
    contains the domain specific logic for handling Document events
    """
    COLUMN_PAGE_ID = 0
    COLUMN_TOOLTIP = 1
    COLUMN_FILENAME = 2
    COLUMN_THUMB = 3
    COLUMN_ORDER = 4
    COLUMN_HASH = 5

    def __init__(self, document: Document):
        """
        Initializes the underlying ListStore and fills it with a row for each page, then start the lazy loading

        The actual image and data loading happens in _load_row
        """
        columns = {
            self.COLUMN_PAGE_ID: str,
            self.COLUMN_TOOLTIP: str,
            self.COLUMN_FILENAME: str,
            self.COLUMN_THUMB: GdkPixbuf.Pixbuf,
            self.COLUMN_ORDER: int
            # self.COLUMN_HASH: str file hash = filename + modified_time (gets added by LazyLoadingListStore)
        }
        super().__init__(*(columns.values()), init_row=self._init_row, load_row=self._load_row, hash_row=self._hash_row)
        self.document = document
        # noinspection PyCallByClass,PyArgumentList
        self.loading_image_pixbuf = GdkPixbuf.Pixbuf.new_from_resource(
            '/org/readmachine/ocrd-browser/icons/loading.png')

        file_lookup = self._get_image_paths(self.document)
        order = count(start=1)
        for page_id in self.document.page_ids:
            file = str(file_lookup[page_id])
            self.append((page_id, '', file, None, next(order)))

        for row in self:
            print(row[:])
        GLib.timeout_add(10, self.start_loading)

    def get_row_by_page_id(self, page_id: str) -> RowResult:
        """
        Find index and row by page_id
        """
        return self.get_row_by_column_value(self.COLUMN_PAGE_ID, page_id)

    def get_row_by_column_value(self, column, value) -> RowResult:
        """
        Find index and row by column value
        """
        for n, row in enumerate(self):
            if row[column] == value:
                return n, row
        return None, None

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

    def document_changed(self, subtype: str, page_ids: Union[List[str], Dict[str, str]]):
        """
        Event callback to sync Document modifications with the ListStore

        @param subtype: str one of  'page_added', 'page_deleted', 'page_changed', 'reordered'
        @param page_ids: List[str] affected page_ids
        """

        def _page_added(page_ids_: List[str]):
            for page_id in page_ids_:
                file = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=page_id)[0]
                file_name = str(self.document.path(file.local_filename))
                self.append((page_id, '', file_name, None, len(self)))

        def _page_deleted(page_ids_: List[str]):
            for delete_page_id in reversed(page_ids_):
                n, row = self.get_row_by_page_id(delete_page_id)
                self.remove(self.get_iter(Gtk.TreePath(n)))

        def _page_changed(page_ids_: List[str]):
            for page_id in page_ids_:
                n, row = self.get_row_by_page_id(page_id)
                files = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=page_id)
                if files:
                    file_name = str(self.document.path(files[0]))
                    row[self.COLUMN_FILENAME] = file_name

        def _reordered(old_to_new_ids: Dict[str, str]):
            id_to_position: Dict[str, int] = {}
            for n, row in enumerate(self):
                id_to_position[row[self.COLUMN_PAGE_ID]] = n

            positions: List[int] = list(range(0, len(old_to_new_ids)))
            for old, new in old_to_new_ids.items():
                positions[id_to_position[old]] = id_to_position[new]

            self.reorder(positions)

            # Update the order in the ListStore data, not needed for now, but might help if we have sorting
            order = count(start=1)
            for page_id in self.document.page_ids:
                n, row = self.get_row_by_page_id(page_id)
                row[self.COLUMN_ORDER] = next(order)

        handler = {
            'page_added': _page_added,
            'page_deleted': _page_deleted,
            'page_changed': _page_changed,
            'reordered': _reordered,
        }
        handler[subtype](page_ids)

    @staticmethod
    def _get_image_paths(document: Document, file_group='OCR-D-IMG') -> Dict[str, Path]:
        """
        Builds a Dict ID->Path for all page_ids fast
        """
        images = document.workspace.mets.find_files(fileGrp=file_group)
        page_ids = document.workspace.mets.get_physical_pages(for_fileIds=[image.ID for image in images])
        file_paths = [document.path(image.url) for image in images]
        return dict(zip(page_ids, file_paths))

    def _init_row(self, row: Gtk.TreeModelRow):
        row[1] = 'Loading {}'.format(row[2])
        row[3] = self.loading_image_pixbuf

    @staticmethod
    def _load_row(row):
        filename = row[PageListStore.COLUMN_FILENAME]
        image = cv2.imread(filename)
        row[1] = '{} ({}x{})'.format(filename, image.shape[1], image.shape[0])
        row[3] = cv_to_pixbuf(cv_scale(image, 100, None))
        return row

    @staticmethod
    def _hash_row(row: Gtk.TreeModelRow):
        file = row[PageListStore.COLUMN_FILENAME]
        modified_time = os.path.getmtime(file)
        return '{}:{}'.format(file, modified_time)
