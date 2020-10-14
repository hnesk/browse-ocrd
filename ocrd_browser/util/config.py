import os
from configparser import ConfigParser
from typing import MutableMapping, List

from gi.repository import GLib
from ocrd_utils import getLogger


class _FileGroups:
    def __init__(self, section: MutableMapping):
        preferred_images = section.get('preferredImages', 'OCR-D-IMG, OCR-D-IMG.*')
        self.preferred_images: List[str] = [grp.strip() for grp in preferred_images.split(',')]

class _Settings:
    def __init__(self, config: ConfigParser):
        self.file_groups = _FileGroups(config['FileGroups'] if config.has_section('FileGroups') else {})


    @classmethod
    def build_default(cls, config_dirs = None) -> '_Settings':
        if config_dirs is None:
            config_dirs = GLib.get_system_config_dirs() + [GLib.get_user_config_dir()] + [os.getcwd()]

        config_files = [dir + '/ocrd-browser.conf' for dir in config_dirs]
        return cls.build_from_files(config_files)


    @classmethod
    def build_from_files(cls, files) -> '_Settings':
        log = getLogger('ocrd_browser.util.config._Settings.build_from_files')
        config = ConfigParser()
        config.optionxform = lambda option: option
        read_files = config.read(files)
        log.debug('Read config files: %s', ', '.join(read_files))
        return cls(config)


SETTINGS = _Settings.build_default()
