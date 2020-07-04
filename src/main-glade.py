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

class ScanApplication(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.readmachine.scanview",flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,**kwargs)
        self.base_path = Path(__file__).absolute().parent.parent
        self.window = None
        self.preview_height = 600
        self.left_preview = None
        self.right_preview = None
        self.left_image = None
        self.right_image = None
        self.left_layout = None
        self.right_layout = None
        self.driver = None
        self.about_dialog = None
        self.count = 0
        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Command line test", None)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.build()
        self.connect()

        #self.driver = AndroidADBDriver()
        self.driver = DummyDriver('/home/jk/Projekte/archive-tools/projects/exit1/orig/')
        self.driver.setup()

        self.document = Document.create()

    def build(self):
        builder = Gtk.Builder()
        builder.add_from_file(str(self.base_path / "src/glade/scanview.glade"))
        builder.add_from_file(str(self.base_path / "src/glade/menu.ui"))
        #builder.connect_signals(self)

        #self.set_menubar(builder.get_object("app-menu"))
        self.set_app_menu(builder.get_object("app-menu"))
        self.window = builder.get_object('main')
        self.window.set_application(self)
        self.left_preview = builder.get_object('main.page.left')
        self.right_preview = builder.get_object('main.page.right')
        self.scroller = builder.get_object('main.scroll')

        self.about_dialog = builder.get_object('dlg_about')

    def connect(self):
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        action = Gio.SimpleAction.new("next", None)
        action.connect("activate", self.on_next)
        self.add_action(action)

        action = Gio.SimpleAction.new("previous", None)
        action.connect("activate", self.on_previous)
        self.add_action(action)

        action = Gio.SimpleAction.new("scan", None)
        action.connect("activate", self.on_scan)
        self.add_action(action)

        #self.scroller.connect('scale-changed', self.on_touch_event)
        #gesture = Gtk.GestureZoom.new(self.window)
        #gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        #gesture.connect("begin", self.zoom_begin)
        #gesture.connect("update", self.zoom_follow)
        #gesture.connect("end", self.zoom_end)
        self.scroller.connect('touch-event', self.on_touch_event)

        self.scroller.connect('size-allocate', self.on_size)

    def on_size(self, widget, allocation):
        self.redraw_images(allocation.height-4)

    def redraw_images(self, height = None):
        update = False
        if height is not None:
            if abs(height - self.preview_height) > 4:
                self.preview_height = height
                update = True
        else:
            update = True

        if update and self.left_image is not None:
            self.left_preview.set_from_pixbuf(image_util.cv_to_pixbuf(image_util.scale(self.left_image, None, self.preview_height)))
            self.right_preview.set_from_pixbuf(image_util.cv_to_pixbuf(image_util.scale(self.right_image, None, self.preview_height)))


    def do_activate(self):
        self.window.present()

    def on_touch_event(self, window, event):
        """

        :param window: GtkScrolledWindow
        :param event: GdkEvent
        :return:
        """

        print(event.sequence)
        #for e in event.sequence:
        #    print(e)


    def zoom_begin(self, gesture, widget):
        print('zb')
        print(gesture.get_scale_delta())

    def zoom_follow(self, gesture, widget):
        print('zf')
        print(gesture.get_scale_delta())

    def zoom_end(self, gesture, sequence):
        print('ze')
        print(gesture.get_scale_delta())


    def on_previous(self, action, parameter):
        print(action.get_name())

    def on_next(self, action, parameter):
        print(action.get_name())


    def on_scan(self, action, parameter):
        try:
            img = self.driver.scan()
            print(str(img))
            image = cv2.imread(str(img))
            pw = PageWarper(image)
        except Exception as err:
            print(err)
            #raise err
            # print('PW: ' + str(err))
            return

        if not self.left_layout:
            self.left_layout, self.right_layout = pw.guess_layouts(0.1,0.65,0.5,-0.15,300)

        try:
            #left_layout = LayoutInfo(0, 0, 0, 0, 5.2, 8.0, 600)
            self.left_image = pw.get_warped_image(self.left_layout, False)
            self.right_image = pw.get_warped_image(self.right_layout, True)
        except Exception as err:
            print('Warp: ' + str(err))


        self.redraw_images()

        self.document.add_image(self.left_image)
        self.document.add_image(self.right_image)
        self.document.save()




    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()
        #print(options)

        self.activate()
        return 0


    def on_about(self, action, param):
        self.about_dialog.present()

    def on_quit(self, action, param):
        self.quit()


def main(arguments):
    app = ScanApplication()
    app.run(arguments)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
