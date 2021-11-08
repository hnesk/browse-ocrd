import unittest

from tests import TestCase
from ocrd_browser.util.file_groups import best_file_group, weight_match


class FileGroupsTestCase(TestCase):

    def setUp(self) -> None:
        self.test_groups = [
            ('OCR-D-SEG-BLOCK-tesseract', 'application/vnd.prima.page+xml'),
            ('OCR-D-GT-PAGE', 'application/vnd.prima.page+xml'),
            ('OCR-D-IMG', 'image/tiff'),
            ('OCR-D-IMG-BIN', 'image/tiff'),
        ]

    def test_weight_match(self):
        self.assertEqual(0, weight_match('ABC', []))
        self.assertEqual(1, weight_match('ABC', ['ABC']))
        self.assertEqual(1, weight_match('ABC', ['ABC', 'DEF']))
        self.assertEqual(0.5, weight_match('DEF', ['ABC', 'DEF']))
        self.assertEqual(0, weight_match('DEF', ['ABC']))

    def test_weight_match_re(self):
        self.assertEqual(1, weight_match('ABC', [r'AB[CD]']))
        # 1.0 for match ABC + 0.5 match \w{3}
        self.assertEqual(1.5, weight_match('ABC', ['ABC', r'\w{3}']))

    def test_best_file_group_prefers_shortest_file_group_if_no_other_preferences(self):
        expected = ('OCR-D-IMG', 'image/tiff')
        actual = best_file_group(self.test_groups)
        self.assertEqual(expected, actual)

    def test_best_file_group_prefers_by_mimetype(self):
        expected = ('OCR-D-GT-PAGE', 'application/vnd.prima.page+xml')
        actual = best_file_group(self.test_groups, preferred_mimetypes=[r'application/.*'])
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
