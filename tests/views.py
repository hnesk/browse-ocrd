import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio

import unittest
import warnings
from pathlib import Path


class TestCaseWithResources(unittest.TestCase):
    resources = None

    @classmethod
    def setUpClass(cls) -> None:
        warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
        base_bath = Path(__file__).absolute().parent.parent
        cls.resources = Gio.resource_load(str(base_bath / "ocrd_browser/ui.gresource"))
        Gio.resources_register(cls.resources)

    @classmethod
    def tearDownClass(cls) -> None:
        Gio.resources_unregister(cls.resources)


class ViewManagerTestCase(TestCaseWithResources):

    def setUp(self):
        from ocrd_browser.views import ViewManager, ViewImages
        self.vm = ViewManager({'images': ViewImages})

    def test_get_view_options(self):
        expected = {'images': 'ViewImages'}
        actual = self.vm.get_view_options()
        self.assertEqual(expected, actual)

    def test_get_view(self):
        from ocrd_browser.views import ViewImages
        expected = ViewImages
        actual = self.vm.get_view('images')
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
