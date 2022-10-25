import unittest
from ocrd_browser.view import ViewImages, ViewRegistry
from tests import TestCase


class ViewManagerTestCase(TestCase):

    def setUp(self):
        self.vm = ViewRegistry({'images': (ViewImages, 'Images', 'Displays Images')})

    def test_get_view_options(self):
        expected = {'images': 'Images'}
        actual = self.vm.get_view_options()
        self.assertEqual(expected, actual)

    def test_get_view(self):
        expected = ViewImages
        actual = self.vm.get_view('images')
        self.assertEqual(expected, actual)

    def test_create_from_entry_points_doesnt_throw(self):
        vr = ViewRegistry.create_from_entry_points()
        self.assertIsInstance(vr, ViewRegistry)


if __name__ == '__main__':
    unittest.main()
