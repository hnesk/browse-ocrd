from typing import Tuple, Optional

from gi.repository import GObject, Gtk, GLib

import concurrent.futures


class LazyLoadingListStore(Gtk.ListStore):
    init_row = GObject.Property()
    load_row = GObject.Property()
    hash_row = GObject.Property()

    def __init__(self, *column_types, init_row, load_row, hash_row):
        column_types = list(column_types)
        column_types.append(str)
        super().__init__(*column_types)
        self.init_row = init_row
        self.load_row = load_row
        self.hash_row = hash_row
        self.futures = None
        self.row_inserted_handler = self.connect('row-inserted', self._on_row_inserted)
        self.row_changed_handler = self.connect('row-changed', self._on_row_changed)

    def get_row_by_column_value(self, column, value) -> Tuple[Optional[int], Optional[Gtk.TreeModelRow]]:
        """
        Find index and row by column value
        """
        for n, row in enumerate(self):
            if row[column] == value:
                return n, row
        return None, None

    def start_loading(self):
        self.futures = {}
        self.submit_all()
        GLib.idle_add(self._collect_workers().__next__, priority=GLib.PRIORITY_DEFAULT_IDLE)

    def submit_all(self):
        pool = concurrent.futures.ThreadPoolExecutor()
        for row in self:
            self._submit_future(row, pool)
        pool.shutdown(wait=False)
        return True

    def _submit_future(self, row, pool=None):
        if self.futures is None:
            return
        own_pool = pool is None
        if own_pool:
            pool = concurrent.futures.ThreadPoolExecutor()

        row_hash = self.hash_row(row)

        if row[-1] != row_hash and row not in self.futures.values():
            future = pool.submit(self.load_row, row[:])
            self.futures[future] = row

        if own_pool:
            pool.shutdown(wait=False)

    def _do_insert(self, position, row):
        if row is not None:
            row = tuple(row) + (None,)
        super()._do_insert(position, row)

    def _on_row_inserted(self, list_store: Gtk.ListStore, _path: Gtk.TreePath, it: Gtk.TreeIter):
        row = list_store[it]
        with self.handler_block(self.row_changed_handler):
            self.init_row(row)
        self._submit_future(row)

    def _on_row_changed(self, list_store: Gtk.ListStore, _path: Gtk.TreePath, it: Gtk.TreeIter):
        row = list_store[it]
        self._submit_future(row)

    def _collect_workers(self):
        for future in concurrent.futures.as_completed(self.futures):
            row = self.futures.pop(future)
            try:
                new_row_data = future.result()
            except Exception as exc:
                print('{} generated an exception: {}'.format(row[0], exc))
            else:
                with self.handler_block(self.row_changed_handler):
                    for i, (old, new) in enumerate(zip(row[:], new_row_data)):
                        if old != new:
                            row[i] = new_row_data[i]
                    row[-1] = self.hash_row(row)
                yield True
        # Futures are finished for now, check back every 50ms if there is something new
        GLib.timeout_add(50, self._collect_workers().__next__, priority=GLib.PRIORITY_DEFAULT_IDLE)
        yield False
