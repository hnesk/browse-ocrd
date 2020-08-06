from tests import TestCase, ASSETS_PATH
from ocrd_browser.model import Document


class DocumentTestCase(TestCase):

    def setUp(self):
        self.doc = Document.load(ASSETS_PATH / 'kant_aufklaerung_1784/data/mets.xml')

    def test_get_page_ids(self):
        self.assertEqual(['PHYS_0017','PHYS_0020'], self.doc.page_ids)

    def test_reorder(self):
        self.doc.reorder(['PHYS_0020','PHYS_0017'])
        self.assertEqual(['PHYS_0020','PHYS_0017'], self.doc.page_ids)

    def test_reorder_with_wrong_ids_raises_value_error(self):
        with self.assertRaises(ValueError) as context:
            self.doc.reorder(['PHYS_0021','PHYS_0017'])

        self.assertIn('page_ids do not match', str(context.exception))
