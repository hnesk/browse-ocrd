from tests import TestCase, TEST_BASE_PATH
from ocrd_browser.model import Document


class PageTestCase(TestCase):

    def setUp(self):
        self.doc = Document.load(TEST_BASE_PATH / 'example/workspaces/aletheiaexamplepage/mets.xml')

    def test_xpath_works_with_different_namespaces(self):
        for page_id in ['PAGE_2017', 'PAGE_2018', 'PAGE_2019']:
            page = self.doc.page_for_id(page_id, 'OCR-D-GT-PAGE')
            xpath_result = page.xpath('/page:PcGts/page:Page/@imageFilename')
            self.assertGreater(len(xpath_result), 0)
