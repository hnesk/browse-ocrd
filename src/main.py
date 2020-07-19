#!/usr/bin/env python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: t; c-basic-offset: 4; tab-width: 4 -*-
import gi
import sys
import cv2
import image_util

from voussoir.pagewarper import PageWarper, LayoutInfo
from scandriver import DummyDriver, AndroidADBDriver
from model import Document
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio

BASE_PATH = Path(__file__).absolute().parent.parent
RESOURCE_FILE_NAME = "resources/ocrdbrowser.gresource"



class ScanApplication(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.readmachine.ocrdbrowser", **kwargs)
        self.base_path = Path(__file__).absolute().parent.parent
        self.window = None
        self.preview_height = 600
        self.left_preview = None
        self.right_preview = None
        self.scroller = None
        self.left_image = None
        self.right_image = None
        self.left_layout = None
        self.right_layout = None
        self.driver = None
        self.about_dialog = None
        self.actions = {}
        self.count = 0
        self.listview = None


    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.document = Document.create()

        self.connect()

        # self.driver = AndroidADBDriver()
        self.driver = DummyDriver('/home/jk/Projekte/archive-tools/projects/exit1/orig/')
        self.driver.setup()


    def connect(self):
        for action in ('first','previous','next','last','add','scan', 'about', 'quit'):
            self.actions[action] = self.create_simple_action(action)

        self.scroller.connect('size-allocate', self.on_size)

    def create_simple_action(self, name, callback = None):
        callback = callback if callback else getattr(self, 'on_'+name)
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        return action


    def on_size(self, widget, allocation):
        self.redraw_images(allocation.height - 4)

    def redraw_images(self, height=None):
        update = False
        if height is not None:
            if abs(height - self.preview_height) > 4:
                self.preview_height = height
                update = True
        else:
            update = True

        if update and self.left_image is not None:
            self.left_preview.set_from_pixbuf(
                image_util.cv_to_pixbuf(image_util.cv_scale(self.left_image, None, self.preview_height)))
            self.right_preview.set_from_pixbuf(
                image_util.cv_to_pixbuf(image_util.cv_scale(self.right_image, None, self.preview_height)))



    def on_scan(self, action, parameter):
        try:
            img = self.driver.scan()
            print(str(img))
            image = cv2.imread(str(img))
            pw = PageWarper(image)
        except Exception as err:
            print(err)
            return

        if not self.left_layout:
            self.left_layout, self.right_layout = pw.guess_layouts(0.1, 0.65, 0.5, -0.15, 300)

        try:
            # left_layout = LayoutInfo(0, 0, 0, 0, 5.2, 8.0, 600)
            self.left_image = pw.get_warped_image(self.left_layout, False)
            self.right_image = pw.get_warped_image(self.right_layout, True)
        except Exception as err:
            print('Warp: ' + str(err))

        self.redraw_images()
        self._update_ui()

    def on_add(self, action, param):
        self.document.add_images((self.left_image, self.right_image))
        self.document.save()
        self._update_ui()



def main(arguments):
    from application import OcrdBrowserApplication
    app = OcrdBrowserApplication()
    app.run(arguments)



def install_excepthook():
    """ Make sure we exit when an unhandled exception occurs. """
    old_hook = sys.excepthook
    def new_hook(etype, evalue, etb):
        old_hook(etype, evalue, etb)
        while Gtk.main_level():
            Gtk.main_quit()
        sys.exit()
    sys.excepthook = new_hook




if __name__ == "__main__":
    resources = Gio.resource_load(str(BASE_PATH / RESOURCE_FILE_NAME))
    Gio.resources_register(resources)
    install_excepthook()
    sys.exit(main(sys.argv))
