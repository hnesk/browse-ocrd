import os
from configparser import ConfigParser
from typing import List

from gi.repository import GLib


class _Settings:

    def __init__(self, config: ConfigParser):
        self.preferredGroups = ['OCR-D-IMG', 'OCR-D-IMG-*', 'ORIGINAL']
        if 'General' in config:
            general = config['General']
            if 'preferredGroups' in general:
                self.preferredGroups = [grp.strip() for grp in general['preferredGroups'].split(',')]


    @classmethod
    def _build(cls, dirs: List[str]) -> '_Settings':
        files = [dir + '/ocrd-browser.conf' for dir in dirs]
        config = ConfigParser()
        config.optionxform = lambda option: option
        config.read(files)
        return cls(config)


SETTINGS = _Settings(GLib.get_system_config_dirs() + [GLib.get_user_config_dir()] + [os.getcwd()])

