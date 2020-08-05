import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib

import unittest
from ocrd_browser.ui import LazyLoadingListStore


class LazyLoadingListStoreTestCase(unittest.TestCase):

    def setUp(self):
        def call_instantly(fun, *args, **kwargs):
            return fun(*args, **kwargs)

        self.types = (str, int, GdkPixbuf.Pixbuf)
        self.list_store = Gtk.ListStore(*self.types)
        self.lazy_list_store = LazyLoadingListStore(*self.types, init_row=self.logging_init, load_row=self.logging_load,
                                                    hash_row=self.hash_row)
        self.init_log = []
        self.backup_idle_add = GLib.idle_add
        GLib.idle_add = call_instantly

    def tearDown(self) -> None:
        GLib.idle_add = self.backup_idle_add

    def logging_init(self, row: Gtk.TreeModelRow):
        self.init_log.append(row[:])

    def logging_load(self, row: Gtk.TreeModelRow):
        pass
        # self.init_log.append(row[:])

    def hash_row(self, row: Gtk.TreeModelRow):
        return row[0]

    def test_constructor_propagates_types(self):
        for i in range(0, self.list_store.get_n_columns()):
            self.assertEqual(self.list_store.get_column_type(i), self.lazy_list_store.get_column_type(i))

    def test_constructor_adds_hash_column(self):
        list_width = self.list_store.get_n_columns()
        lazy_list_width = self.lazy_list_store.get_n_columns()
        self.assertEqual(list_width + 1, lazy_list_width)
        hash_column_type = self.lazy_list_store.get_column_type(lazy_list_width - 1)
        str_as_gtype = GObject.GType.from_name('gchararray')
        self.assertEqual(str_as_gtype, hash_column_type)

    def test_append_adds_hash_column(self):
        row_data = ('a', 5, None)
        self.lazy_list_store.append(row_data)
        actual = self.lazy_list_store[-1][:]
        self.assertSequenceEqual(row_data + (None,), actual)

    def test_append_calls_init_row(self):
        row_data = ('a', 5, None)
        self.lazy_list_store.append(row_data)
        self.assertEqual(1, len(self.init_log))
        self.assertSequenceEqual(row_data, self.init_log[0][:len(row_data)])

    def test_init_row_can_modify_model(self):
        def change_row(row: Gtk.TreeModelRow):
            row[1] = 15

        self.lazy_list_store.init_row = change_row
        self.lazy_list_store.append(('a', 5, None))
        self.assertEqual(self.lazy_list_store[-1][1], 15)


if __name__ == '__main__':
    unittest.main()
