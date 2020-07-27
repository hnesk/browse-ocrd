import unittest
from ocrd_browser.extensions.xmlview import ViewXml
from ocrd_browser.model import Document


class XmlViewTestCase(unittest.TestCase):

    def setUp(self):
        self.vx = ViewXml(document=Document.create())

    def test_can_construct(self):
        self.assertIsNotNone(self.vx)


if __name__ == '__main__':
    unittest.main()
