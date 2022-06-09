from tests import TestCase, TEST_BASE_PATH, ASSETS_PATH
from ocrd_browser.model import Document, IMAGE_FROM_PAGE_FILENAME_SUPPORT


class PageTestCase(TestCase):

    def test_xpath_works_with_different_namespaces(self):
        doc = Document.load(TEST_BASE_PATH / 'example/workspaces/aletheiaexamplepage/mets.xml')
        for page_id in ['PAGE_2017', 'PAGE_2018', 'PAGE_2019']:
            page = doc.page_for_id(page_id, 'OCR-D-GT-PAGE')
            xpath_result = page.xpath('/page:PcGts/page:Page/@imageFilename')
            self.assertGreater(len(xpath_result), 0)

    def test_can_call_get_image_if_supported(self):
        page = Document.load(ASSETS_PATH / 'kant_aufklaerung_1784-binarized/data/mets.xml').page_for_id('P_0017', 'OCR-D-GT-WORD')
        if IMAGE_FROM_PAGE_FILENAME_SUPPORT:
            image_by_feature, _, _ = page.get_image(feature_selector={'binarized'}, feature_filter={'cropped'})
            image_by_filename, _, _ = page.get_image(filename='OCR-D-IMG-BIN/BIN_0017.png', feature_filter={'cropped'})
            self.assertEqual(image_by_feature, image_by_filename)
        else:
            try:
                page.get_image(filename='OCR-D-GT-IMG-BIN/PAGE_2019.tif')
                self.fail('IMAGE_FROM_PAGE_FILENAME_SUPPORT detected wrong')
            except RuntimeError as e:
                self.assertTrue(str(e).startswith('Parameter filename not supported in '))

    def test_missing_image(self):
        doc = Document.load((TEST_BASE_PATH / 'example/workspaces/kant_aufklaerung_1784_missing_image/mets.xml').as_uri())
        page = doc.page_for_id('PHYS_0017', 'OCR-D-GT-PAGE')
        image, info, exif = page.get_image(feature_selector='', feature_filter='binarized')
        # Assert no exceptions happened but image is None
        self.assertIsNone(image)
