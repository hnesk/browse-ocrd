import os
import re
import unittest

from pydantic import ValidationError

from ocrd_browser.util.config import Settings, SettingsFactory
from tests import TestCase, TEST_BASE_PATH


class SettingsTestCase(TestCase):

    def setUp(self) -> None:
        self.settings = SettingsFactory.build_from_files([TEST_BASE_PATH / 'example/config/simple.conf'])

    def test_value_default_no_config_file(self) -> None:
        settings = SettingsFactory.build_from_files([])
        self.assertEqual([re.compile('OCR-D-IMG'), re.compile('OCR-D-IMG.*')], settings.file_groups.preferred_images)

    def test_value_default(self):
        settings = Settings()
        self.assertEqual([re.compile('OCR-D-IMG'), re.compile('OCR-D-IMG.*')], settings.file_groups.preferred_images)

    def test_value_loaded(self):
        self.assertEqual([re.compile('OCR-D-IMG'), re.compile('OCR-D-IMG.*'), re.compile('ORIGINAL')],
                         self.settings.file_groups.preferred_images)

    def test_value_environment(self):
        os.environ['BROCRD__FILE_GROUPS__PREFERRED_IMAGES'] = 'IMG'
        settings = SettingsFactory.build_from_files([TEST_BASE_PATH / 'example/config/simple.conf'])
        self.assertEqual([re.compile('IMG')], settings.file_groups.preferred_images)
        del os.environ['BROCRD__FILE_GROUPS__PREFERRED_IMAGES']

    def test_value_environment_deep(self):
        os.environ['BROCRD__TOOL__PAGEVIEWER__COMMANDLINE'] = 'ls {file.path.absolute}'
        settings = SettingsFactory.build_from_files([TEST_BASE_PATH / 'example/config/simple.conf'])
        self.assertEqual('ls {file.path.absolute}', settings.tool['pageviewer'].commandline)
        del os.environ['BROCRD__TOOL__PAGEVIEWER__COMMANDLINE']

    def test_tools(self):
        pv = self.settings.tool['pageviewer']
        self.assertEqual(
            '/usr/bin/java -jar /home/jk/bin/JPageViewer/JPageViewer.jar --resolve-dir {workspace.directory} {file.path.absolute}',
            pv.commandline)
        self.assertEqual('p', pv.shortcut)

    def test_tool_command_validate_command(self):
        with self.assertRaises(ValidationError) as context:
            Settings(tool={'abc': {'commandline': '/je/not/existe/ {file.path.absolute}'}})
        self.assertIn('Command "/je/not/existe/" not found', str(context.exception))

    def test_tool_command_validate_placeholder(self):
        with self.assertRaises(ValidationError) as context:
            Settings(tool={'abc': {'commandline': 'ls {file.path.absolu}'}})
        self.assertIn("has no attribute 'absolu'", str(context.exception))


if __name__ == '__main__':
    unittest.main()
