import os
from collections import OrderedDict
from configparser import ConfigParser
import shlex
from typing import List, Optional, MutableMapping
from shutil import which

from gi.repository import GLib
from ocrd_utils import getLogger

ConfigDict = MutableMapping[str, str]


class _SubSettings:
    @classmethod
    def from_section(cls, _name: str, section: ConfigDict) -> '_SubSettings':
        raise NotImplementedError('please override from_section')

    def validate(self) -> None:
        pass

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, repr(vars(self)))


class _FileGroups(_SubSettings):
    def __init__(self, preferred_images: List[str]):
        self.preferred_images = preferred_images

    @classmethod
    def from_section(cls, _name: str, section: ConfigDict) -> '_FileGroups':
        preferred_images = section.get('preferredImages', 'OCR-D-IMG, OCR-D-IMG.*')
        return cls(
            [grp.strip() for grp in preferred_images.split(',')]
        )


class _Tool(_SubSettings):
    PREFIX = 'Tool '

    def __init__(self, name: str, commandline: str, shortcut: Optional[str] = None):
        self.name = name
        self.commandline = commandline
        self.shortcut = shortcut

    def validate(self) -> None:
        executable = shlex.split(self.commandline)[0]
        resolved = which(executable)
        if not resolved:
            raise ValueError('Could not locate executable "{}"'.format(executable))

    @classmethod
    def from_section(cls, name: str, section: ConfigDict) -> '_Tool':
        return cls(
            name[len(cls.PREFIX):],
            section['commandline'],
            section.get('shortcut', None)
        )


class Settings:

    _settings = None

    def __init__(self, config: ConfigParser, validate: bool = True):
        self.file_groups = _FileGroups.from_section('FileGroups', config['FileGroups'] if 'FileGroups' in config else {'': ''})
        if validate:
            self.file_groups.validate()
        self.tools = OrderedDict()
        for name, section in config.items():
            if name.startswith(_Tool.PREFIX):
                tool = _Tool.from_section(name, section)
                if validate:
                    tool.validate()
                self.tools[tool.name] = tool

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, repr(vars(self)))

    @classmethod
    def get(cls) -> 'Settings':
        if cls._settings is None:
            cls._settings = Settings.build_default()
        return cls._settings

    @classmethod
    def build_default(cls, config_dirs: Optional[List[str]] = None, validate: bool = True) -> 'Settings':
        if config_dirs is None:
            config_dirs = GLib.get_system_config_dirs() + [GLib.get_user_config_dir()]
            try:
                config_dirs.append(os.getcwd())
            except FileNotFoundError:
                # ignore deleted cwd in unit tests
                pass

        config_files = [dir_ + '/ocrd-browser.conf' for dir_ in config_dirs]
        return cls.build_from_files(config_files, validate)

    @classmethod
    def build_from_files(cls, files: List[str], validate: bool = True) -> 'Settings':
        log = getLogger('ocrd_browser.util.config._Settings.build_from_files')
        config = ConfigParser()
        setattr(config, 'optionxform', lambda option: option)
        read_files = config.read(files)
        log.info('Read %d config file(s): %s, tried %s', len(read_files), ', '.join(read_files), ', '.join(str(file) for file in files))
        return cls(config, validate)
