#!/usr/bin/env python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 4 -*-
import sys

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')

gi.require_version('WebKit2', '4.0')

from gi.repository import Gtk, Gio  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Type  # noqa: E402
from types import TracebackType  # noqa: E402

BASE_PATH = Path(__file__).absolute().parent
resources = Gio.resource_load(str(BASE_PATH / "ui.gresource"))
Gio.resources_register(resources)


def install_excepthook() -> None:
    """ Make sure we exit when an unhandled exception occurs. """
    old_hook = sys.excepthook

    def new_hook(type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
        old_hook(type_, value, traceback)
        while Gtk.main_level():
            Gtk.main_quit()
        sys.exit()

    sys.excepthook = new_hook


def main() -> None:
    from ocrd_utils import initLogging
    initLogging()
    from ocrd_browser.application import OcrdBrowserApplication
    install_excepthook()
    app = OcrdBrowserApplication()
    app.run(sys.argv)


if __name__ == "__main__":
    # WHY OH WHY
    sys.path.append(str(BASE_PATH.parent))
    main()
    sys.exit()
