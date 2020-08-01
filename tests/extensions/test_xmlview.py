import unittest
from unittest.mock import MagicMock
from ocrd_browser.extensions.xmlview import ViewXml
from ocrd_browser.model import Document

class XmlViewTestCase(unittest.TestCase):

    def setUp(self):
        self.vx = ViewXml('unique',document=MagicMock(spec=Document))

    def test_can_construct(self):
        self.assertIsNotNone(self.vx)


if __name__ == '__main__':
    unittest.main()
