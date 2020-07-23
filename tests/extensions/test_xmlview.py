import gi

from tests.test_views import TestCaseWithResources

gi.require_version('Gtk', '3.0')

import unittest


class XmlViewTestCase(TestCaseWithResources):

    def setUp(self):
        from ocrd_browser.extensions.xmlview import ViewXml
        from ocrd_browser.model import Document
        self.vx = ViewXml(document = Document.create())

    def test_can_construct(self):
        self.assertIsNotNone(self.vx)


if __name__ == '__main__':
    unittest.main()
