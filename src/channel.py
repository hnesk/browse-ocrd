import os
import gi
import logging
from logging import NullHandler
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

logging.getLogger(__name__).addHandler(NullHandler())

class Channel:

    def __init__(self, filename, responder):
        self.filename = filename
        self.responder = responder
        self.pipe = None
        self.watch = None
        self.logger = logging.getLogger(__name__)

    def open(self):
        try:
            os.mkfifo(self.filename)
        except OSError as err:
            self.logger.debug('Could not create pipe, Error: %s', err)
            pass
        try:
            self.pipe = os.open(self.filename, os.O_RDONLY | os.O_NONBLOCK)
            self.watch = GLib.io_add_watch(self.pipe, GLib.IO_IN, self.check)
        except OSError as err:
            self.logger.error('Could not open pipe, Error: %s', err)
        return self

    def close(self):
        if self.watch:
            GLib.source_remove(self.watch)
        if self.pipe:
            os.close(self.pipe)

        # os.remove(self.filename)

    def check(self, fd, condition):
        if condition != GLib.IO_IN:
            return

        inp = None
        try:
            inp = os.read(fd, 1024)
        except OSError as err:
            if err.errno != 11:
                raise err
        if inp:
            try:
                command, *args = inp.decode().strip().split(' ', maxsplit=1)
                command_name = 'command_' + command
                if hasattr(self.responder, command_name):
                    getattr(self.responder, command_name)(*args)
                else:
                    self.logger.debug('missing command %s in %s', command_name, type(self.responder))
            except Exception as err:
                self.logger.error('Exception in command %s, %s', command_name, err)

        return True
