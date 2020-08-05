"""
Fixes warnings about unspecified version contraints a la:
PyGIWarning: GtkSource was imported without specifying a version first. Use gi.require_version('GtkSource', '4') before import to ensure that the right version gets loaded.

import with:

  import tests

in your Gtk using test file in the first line
"""
# pylint: disable=unused-import
from unittest import TestCase
import gi
from pathlib import Path
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')

ASSETS_PATH = (Path(__file__).parent/ 'assets').absolute()
if not ASSETS_PATH.exists():
    raise RuntimeError('Assset path {} not found, please run: make tests/assets first')


