import unittest

from ocrd_browser.util.config import Settings
from tests import TestCase, TEST_BASE_PATH


class SettingsTestCase(TestCase):

    def setUp(self) -> None:
        self.settings = Settings.build_from_files([TEST_BASE_PATH / 'example/config/simple.conf'], validate=False)

    def test_default_value(self):
        settings = Settings({})
        self.assertEqual(['OCR-D-IMG', 'OCR-D-IMG.*'], settings.file_groups.preferred_images)

    def test_loaded_value(self):
        self.assertEqual(['OCR-D-IMG', 'OCR-D-IMG.*', 'ORIGINAL'], self.settings.file_groups.preferred_images)

    def test_tools(self):
        pv = self.settings.tools['PageViewer']
        self.assertEqual(
            '/usr/bin/java -jar /home/jk/bin/JPageViewer/JPageViewer.jar --resolve-dir {workspace.directory} {file.path.absolute}',
            pv.commandline)
        self.assertEqual('p', pv.shortcut)

        pv = self.settings.tools['Open']
        self.assertEqual('xdg-open {file.path.absolute}', pv.commandline)
        self.assertEqual('o', pv.shortcut)


if __name__ == '__main__':
    unittest.main()
