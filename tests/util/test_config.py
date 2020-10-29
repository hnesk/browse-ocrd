import unittest

from ocrd_browser.util.config import _Settings
from tests import TestCase, TEST_BASE_PATH


class SettingsTestCase(TestCase):

    def setUp(self) -> None:
        self.settings = _Settings.build_from_files([TEST_BASE_PATH / 'example' / 'config' / 'simple.conf'])

    def test_default_value(self):
        settings = _Settings({})
        self.assertEqual(['OCR-D-IMG','OCR-D-IMG.*'], settings.file_groups.preferred_images)

    def test_loaded_value(self):
        self.assertEqual(['OCR-D-IMG','OCR-D-IMG.*','ORIGINAL'], self.settings.file_groups.preferred_images)

    def test_tools(self):
        pv = self.settings.tools['PageViewer']
        self.assertEqual('-jar /home/jk/bin/JPageViewer/JPageViewer.jar --resolve-dir . {current}', pv.args)
        self.assertEqual('p', pv.shortcut)

        pv = self.settings.tools['Open']
        self.assertEqual('/usr/bin/xdg-open', pv.executable)
        self.assertEqual('{current}', pv.args)
        self.assertEqual('o', pv.shortcut)

        print(self.settings)





if __name__ == '__main__':
    unittest.main()
