import unittest

from ocrd_browser.util.config import _Settings
from tests import TestCase, TEST_BASE_PATH


class SettingsTestCase(TestCase):

    def setUp(self) -> None:
        self.settings = _Settings.build_from_files([TEST_BASE_PATH / 'example' / 'config' / 'simple.conf'])

    def test_default_value(self):
        settings = _Settings({})
        self.assertEqual(['OCR-D-IMG','OCR-D-IMG.*'], settings.file_groups.preferred_images)

    def test_default_value(self):
        self.assertEqual(['OCR-D-IMG','OCR-D-IMG.*','ORIGINAL'], self.settings.file_groups.preferred_images)

if __name__ == '__main__':
    unittest.main()
