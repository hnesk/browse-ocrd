import shlex
import subprocess
import unittest
from ocrd_utils import setOverrideLogLevel
from pathlib import Path
from typing import Union

from ocrd_browser.model import Document
from ocrd_browser.util.config import _Tool
from ocrd_browser.util.launcher import Launcher
from tests import TestCase, TEST_BASE_PATH, data_provider

BASE_PATH = TEST_BASE_PATH / 'example/workspaces/heavy quoting/'


def quoted(file: Union[str, Path]) -> str:
    return shlex.quote(str(file))


def template_testcases():
    return [
        ('', ''),
        ('{ escaped brace }', '{{ escaped brace }}'),
        (quoted(BASE_PATH), '{workspace.directory}'),
        (quoted(BASE_PATH), '{workspace.baseurl}'),
        (quoted(BASE_PATH / 'mets.xml'), '{workspace.mets_target}'),
        ('--workspace=' + quoted(BASE_PATH), '--workspace={workspace.baseurl}'),
        ('application/vnd.prima.page+xml', '{file.mimetype}'),
        ('PHYS_0017', '{file.pageId}'),
        ('OCR-D-GT-PAGE', '{file.fileGrp}'),
        ('.xml', '{file.extension}'),
        ("'PAGE_0017 PÄGE.xml'", '{file.basename}'),
        ("'PAGE_0017 PÄGE'", '{file.basename_without_extension}'),
        ("'OCR-D-GT PÆGE/PAGE_0017 PÄGE.xml'", '{file.path.relative}'),
        (quoted(BASE_PATH / 'OCR-D-GT PÆGE/PAGE_0017 PÄGE.xml'), '{file.path.absolute}'),
        (quoted(BASE_PATH / 'OCR-D-GT PÆGE/PAGE_0017 PÄGE.xml'), '{file.path}')

    ]


class LauncherTestCase(TestCase):

    def setUp(self) -> None:
        self.launcher = Launcher()
        self.doc = Document.load(BASE_PATH / 'mets.xml')
        self.file = self.doc.files_for_page_id('PHYS_0017', 'OCR-D-GT-PAGE')[0]

    def test_launch_missing(self):
        setOverrideLogLevel('ERROR', True)
        with self.assertLogs('ocrd_browser.util.launcher.Launcher.launch', level='ERROR') as log_watch:
            process = self.launcher.launch('missingtool', self.doc, self.file)
        self.assertIsNone(process)
        self.assertEqual(3, len(log_watch.records))
        self.assertEqual(
            'Tool "missingtool" not found in your config, to fix place the following section in your ocrd-browser.conf',
            log_watch.records[0].getMessage()
        )
        setOverrideLogLevel('OFF', True)

    def test_launch_tool(self):
        tool = _Tool('Echotest', 'echo -n {file.path.relative}')
        with self.launcher.launch_tool(tool, self.doc, self.file, stdout=subprocess.PIPE) as process:
            process.wait()
            result = process.stdout.read().decode('utf8')
        self.assertEqual('OCR-D-GT PÆGE/PAGE_0017 PÄGE.xml', result)

    @data_provider(template_testcases)
    def test_template(self, expected: Union[Path, str], template: str):
        actual = self.launcher._template(template, self.doc, self.file)
        self.assertEqual(str(expected), actual)


if __name__ == '__main__':
    unittest.main()
