from gi.repository import Gtk, GLib

from typing import Callable, Sequence, Dict, Optional, Any, Iterator, Tuple
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

RowLoadCallback = Callable[[Gtk.TreeModelRow], Gtk.TreeModelRow]
RowHashCallback = Callable[[Gtk.TreeModelRow], str]
RowResult = Tuple[Optional[int], Optional[Gtk.TreeModelRow]]


class LazyLoadingListStore(Gtk.ListStore):

    def __init__(self, *column_types: type, load_row: RowLoadCallback, hash_row: RowHashCallback):
        column_type_list = list(column_types)
        column_type_list.append(str)
        super().__init__(*column_type_list)
        self.load_row = load_row
        self.hash_row = hash_row
        self.futures: Optional[Dict[Future[Gtk.TreeModelRow], Gtk.TreeModelRow]] = None
        self.row_inserted_handler = self.connect('row-inserted', self._on_row_inserted)
        self.row_changed_handler = self.connect('row-changed', self._on_row_changed)

    def start_loading(self) -> None:
        self.futures = {}
        self.submit_all()
        GLib.timeout_add(10, self._collect_workers().__next__, priority=GLib.PRIORITY_LOW)

    def submit_all(self) -> bool:
        pool = ThreadPoolExecutor()
        for row in self:
            self._submit_future(row, pool)
        pool.shutdown(wait=False)
        return True

    def _submit_future(self, row: Gtk.TreeModelRow, pool: Optional[ThreadPoolExecutor] = None) -> None:
        if self.futures is None:
            return
        own_pool = pool is None
        if own_pool:
            pool = ThreadPoolExecutor()

        row_hash = self.hash_row(row)

        if row[-1] != row_hash or row not in self.futures.values():
            future = pool.submit(self.load_row, row[:])
            self.futures[future] = row

        if own_pool:
            pool.shutdown(wait=False)

    def _do_insert(self, position: int, row: Sequence[Any]) -> None:
        if row is not None:
            row = tuple(row) + (None,)
        super()._do_insert(position, row)

    def _on_row_inserted(self, list_store: Gtk.ListStore, _path: Gtk.TreePath, it: Gtk.TreeIter) -> None:
        row = list_store[it]
        self._submit_future(row)

    def _on_row_changed(self, list_store: Gtk.ListStore, _path: Gtk.TreePath, it: Gtk.TreeIter) -> None:
        row = list_store[it]
        self._submit_future(row)

    def _collect_workers(self) -> Iterator[bool]:
        for future in as_completed(self.futures):
            row = self.futures.pop(future)
            try:
                new_row_data = future.result()
            except Exception as e:
                import traceback
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                print('#{} generated an exception: {}'.format(row[0], tb))
            else:
                # Dont trigger event 'row-changed' for every single value
                with self.handler_block(self.row_changed_handler):
                    changed = False
                    for i, (old, new) in enumerate(zip(row[:], new_row_data)):
                        if old != new:
                            row[i] = new_row_data[i]
                            changed = True
                    hsh = self.hash_row(row)
                    if hsh != row[-1]:
                        row[-1] = hsh
                        changed = True
                # Trigger event 'row-changed' for the whole changed row
                if changed:
                    n, r = self.get_row_by_column_value(0, row[0])
                    path = Gtk.TreePath(n)
                    self.emit('row-changed', path, self.get_iter(path))

                yield True
        # Futures are finished for now, check back every 50ms if there is something new
        GLib.timeout_add(50, self._collect_workers().__next__, priority=GLib.PRIORITY_LOW)
        yield False

    def get_row_by_column_value(self, column: int, value: str) -> RowResult:
        """
        Find index and row by column value
        """
        for n, row in enumerate(self):
            if row[column] == value:
                return n, row
        return None, None
