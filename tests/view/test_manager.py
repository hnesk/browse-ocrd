import unittest
from unittest.mock import MagicMock

from gi.repository import Gtk
from ocrd_browser.model import Document
from ocrd_browser.view import ViewText, ViewEmpty
from ocrd_browser.ui import MainWindow
from ocrd_browser.view.manager import ViewManager
from tests import TestCase


class ManagerTestCase(TestCase):

    def setUp(self):
        self.root = Gtk.Box(name='container')
        self.win = MagicMock(spec=MainWindow)
        self.win.document = Document.create(self.win)
        self.win.current_page_id = None

        self.vm = ViewManager(self.win, self.root)

    def test_can_construct(self):
        self.assertIsNotNone(self.vm)
        self.assertEqual('container\n', self.vm.print_level())

    def test_one_view(self):
        expected = """
container
\tview_0: ViewText
""".strip()
        self.vm.set_root_view(ViewText)
        self.assertEqual(expected, self.vm.print_level().strip())

    def test_two_views(self):
        expected = """
container
\tGtkPaned
\t\tview_0: ViewText
\t\tview_1: ViewEmpty
""".strip()
        self.vm.set_root_view(ViewText)
        self.vm.split('view_0', ViewEmpty)
        self.assertEqual(expected, self.vm.print_level().strip())

    def test_split_and_close(self):
        expected = """
container
\tGtkPaned
\t\tview_0: ViewText
\t\tview_1: ViewEmpty
""".strip()
        self.vm.set_root_view(ViewText)
        v1 = self.vm.split('view_0', ViewEmpty)
        v2 = self.vm.split(v1.name, ViewEmpty)
        v3 = self.vm.split(v2.name, ViewEmpty)
        self.vm.close(v2.name)
        self.vm.close(v3.name)

        self.assertEqual(expected, self.vm.print_level().strip())


if __name__ == '__main__':
    unittest.main()
