import unittest

from ocrd_browser.util.config import _Settings
from ocrd_browser.util.launcher import Launcher
from tests import TestCase, TEST_BASE_PATH


class LauncherTestCase(TestCase):

    def setUp(self) -> None:
        self.launcher = Launcher()

    def test_template(self):

        self.launcher._template('')





if __name__ == '__main__':
    unittest.main()
