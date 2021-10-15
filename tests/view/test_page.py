import unittest
from unittest.mock import MagicMock
from ocrd_browser.view import ViewPage
from ocrd_browser.ui import MainWindow
from tests import TestCase


class ViewPageTestCase(TestCase):

    def setUp(self):
        self.vx = ViewPage('unique', MagicMock(spec=MainWindow))

    def test_can_construct(self):
        self.assertIsNotNone(self.vx)


if __name__ == '__main__':
    unittest.main()
