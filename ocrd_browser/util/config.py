from __future__ import annotations

import os
import re
import shlex

from collections import defaultdict
from configparser import ConfigParser
from gi.repository import GLib
from ocrd_utils import getLogger
from pydantic import BaseSettings, BaseModel as PydanticBaseModel, Field, validator, Extra
from pydantic.env_settings import SettingsSourceCallable
from shutil import which
from typing import List, Optional, Dict, Any, Tuple


class _DummyObject:
    """
    Dummy object to test formatstrings with nested properties
    """

    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, shlex.quote(v) if isinstance(v, str) else v)


class BaseModel(PydanticBaseModel):
    class Config:
        env_nested_delimiter = '__'
        extra = Extra.forbid


def snake_case(optionstr: str) -> str:
    return re.sub('(?!^)([A-Z]+)', r'_\1', optionstr).lower()


def _split_regexes(cls: Any, v: str) -> List[re.Pattern[str]]:
    """
    Split a string at ',' and returns the parts as compiled regexes
    """
    try:
        return [re.compile(r.strip()) for r in v.split(',')]
    except re.error as e:
        raise ValueError(f'Error in pattern "{e.pattern!r}" @ pos {e.pos}: "{e.msg}"') from e


def _check_commandline(cls: Any, v: str, **placeholders: _DummyObject) -> str:
    """
    Checks for a valid shell command string with placeholders

    1) does the executable exists
    2) Are only existing placeholders used
    """
    executable, *rest = shlex.split(v)
    if not which(executable):
        raise ValueError(f'Command "{executable}" not found: "{v}"')
    try:
        v.format(**placeholders)
    except Exception as e:
        raise ValueError(f'{e!s} in "{v}"') from e
    return v


DUMMY_FILE = _DummyObject(
    ID='ID1',
    basename='IMG1.tif',
    basename_without_extension='IMG1',
    extension='tif',
    fileGrp='IMG',
    loctype='URL',
    mimetype='image/tiff',
    otherloctype=None,
    pageId='PAGE1',
    url='IMG/IMG1.tif',
    path=_DummyObject(absolute='/tmp/test/IMG/IMG1.tif', relative='IMG/IMG1.tif')
)

DUMMY_WORKSPACE = _DummyObject(directory='/tmp/test/', baseurl='/tmp/test/mets.xml')


class FileGroups(BaseModel):
    preferred_images: List[re.Pattern]  # type: ignore[type-arg]

    split_preferred_images = validator('preferred_images', pre=True, allow_reuse=True)(_split_regexes)


class Tool(BaseModel):
    commandline: str
    shortcut: Optional[str]
    name: Optional[str]

    def named(self, name: str) -> Tool:
        self.name = name
        return self

    @validator('commandline')
    def check_commandline(cls, v: str) -> str:
        return _check_commandline(cls, v, file=DUMMY_FILE, workspace=DUMMY_WORKSPACE)


class Settings(BaseSettings):
    file_groups: FileGroups = FileGroups(preferred_images='OCR-D-IMG,OCR-D-IMG.*')
    tool: Dict[str, Tool] = Field({})

    @validator('tool')
    def check_tool(cls, tools: Dict[str, Tool]) -> Dict[str, Tool]:
        return {k.lower(): v.named(k) for k, v in tools.items()}

    class Config:
        env_nested_delimiter = '__'
        extra = Extra.forbid
        env_prefix = 'BROCRD__'

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            """Prioritize ENV over .conf files"""
            return env_settings, init_settings, file_secret_settings


class SettingsFactory:
    _settings = None

    @classmethod
    def settings(cls) -> Settings:
        if cls._settings is None:
            cls._settings = cls.build_from_files(cls.get_default_files())
        return cls._settings

    @classmethod
    def get_default_files(cls) -> List[str]:
        config_dirs = GLib.get_system_config_dirs() + [GLib.get_user_config_dir()]
        try:
            config_dirs.append(os.getcwd())
        except FileNotFoundError:
            # ignore deleted cwd in unit tests
            pass

        return [dir_ + '/ocrd-browser.conf' for dir_ in config_dirs]

    @classmethod
    def build_from_files(cls, files: List[str]) -> Settings:
        log = getLogger('ocrd_browser.util.config.SettingsFactory.build_from_files')
        config = ConfigParser()
        setattr(config, 'optionxform', snake_case)
        read_files = config.read(files)
        log.info('Read %d config file(s): %s, tried %s', len(read_files), ', '.join(read_files),
                 ', '.join(str(file) for file in files))
        settings = Settings(**cls.config_to_dict(config))
        print(settings)
        return settings

    @staticmethod
    def config_to_dict(config: ConfigParser) -> Dict[str, Any]:
        d: Dict[str, Any] = defaultdict(dict)
        for section, values in config.items():
            if section == 'DEFAULT':
                continue
            parts = section.split(' ', 2)
            top = snake_case(parts[0])
            sub = parts[1] if len(parts) > 1 else None
            if sub:
                d[top][sub] = dict(values)
            else:
                d[top] = dict(values)

        return dict(d)
