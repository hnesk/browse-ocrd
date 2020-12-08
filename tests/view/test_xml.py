import unittest
from unittest.mock import MagicMock
from ocrd_browser.view import ViewXml
from ocrd_browser.ui import MainWindow
from tests import TestCase


class XmlViewTestCase(TestCase):

    def setUp(self):
        self.vx = ViewXml('unique', MagicMock(spec=MainWindow))

    def test_can_construct(self):
        self.assertIsNotNone(self.vx)


if __name__ == '__main__':
    unittest.main()
