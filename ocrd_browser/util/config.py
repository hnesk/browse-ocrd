import os
from collections import OrderedDict
from configparser import ConfigParser, SectionProxy
from typing import List, Optional, OrderedDict as OrderedDictType
from shutil import which

from gi.repository import GLib
from ocrd_utils import getLogger

class _SubSettings:
    @classmethod
    def from_section(cls, section: SectionProxy):
        raise NotImplementedError('please override from_section')

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(vars(self)))


class _FileGroups(_SubSettings):
    def __init__(self, preferred_images: List[str]):
        self.preferred_images = preferred_images

    @classmethod
    def from_section(cls, section: SectionProxy):
        preferred_images = section.get('preferredImages', 'OCR-D-IMG, OCR-D-IMG.*')
        return cls(
            [grp.strip() for grp in preferred_images.split(',')]
        )


class _Tool(_SubSettings):

    PREFIX = 'Tool '

    def __init__(self, name: str, executable: str, args: str, shortcut: Optional[str] = None):
        self.name = name
        resolved = which(executable)
        if not resolved:
            raise ValueError('Could not locate executable "{}"'.format(executable))
        self.executable = resolved
        self.args = args
        self.shortcut = shortcut

    @classmethod
    def from_section(cls, section: SectionProxy):
        executable, args = section['commandline'].split(' ', 1)
        return cls(
            section.name[len(cls.PREFIX):],
            executable,
            args,
            section.get('shortcut', None)
        )

class _Settings:
    file_groups: _FileGroups
    tools: OrderedDictType[str, _Tool]


    def __init__(self, config: ConfigParser):
        self.__class__.__annotations__
        self.file_groups = _FileGroups.from_section(config['FileGroups'] if 'FileGroups' in config else {})
        self.tools = OrderedDict()
        for name, section in config.items():
            if name.startswith(_Tool.PREFIX):
                tool = _Tool.from_section(section)
                self.tools[tool.name] = tool

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(vars(self)))


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
