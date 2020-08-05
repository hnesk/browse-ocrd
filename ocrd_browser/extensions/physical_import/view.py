import cv2
from gi.repository import Gtk, Gdk, Gio
from pkg_resources import resource_filename
from typing import List
from voussoir.pagewarper import PageWarper

from ocrd_browser.extensions.physical_import.scandriver import DummyDriver, AndroidADBDriver
from ocrd_browser.image_util import cv_scale, cv_to_pixbuf
from ocrd_browser.view import View
from ocrd_browser.model import DEFAULT_FILE_GROUP


class ViewScan(View):
    """
    Imports book pages from reality
    """

    label = 'Scan'

    def __init__(self, name, window, **kwargs):
        super().__init__(name, window, **kwargs)
        # self.driver = AndroidADBDriver()
        self.driver = DummyDriver('/home/jk/Projekte/archive-tools/projects/exit1/orig/')
        self.driver.setup()

        self.ui: ScanUi = None
        self.previews = []
        self.layouts = []
        self.images = []
        self.selected_page_ids = []

    def build(self):
        super().build()
        self.ui = ScanUi(self)
        self.previews = [self.ui.preview_left, self.ui.preview_right]
        self.viewport.add(self.ui)
        self.window.actions.create('scan', self.on_scan)
        self.window.actions.create('append', self.on_append)
        self.window.actions.create('insert', self.on_insert)
        self.update_ui()

    def on_scan(self, _action: Gio.SimpleAction, _param):
        try:
            file = str(self.driver.scan())
            image = cv2.imread(file)
            pw = PageWarper(image)
        except Exception as err:
            print(err)
            raise err
            return

        if not self.layouts:
            self.layouts = pw.guess_layouts(0.1, 0.65, 0.5, -0.15, 300)

        try:
            self.images = []
            for n, layout in enumerate(self.layouts):
                self.images.append(pw.get_warped_image(layout, n == 1))
        except Exception as err:
            print('Warp: ' + str(err))
        self.redraw()

    def on_append(self, _action: Gio.SimpleAction, _param):
        file_group = DEFAULT_FILE_GROUP
        template_page_id = 'PAGE_{page_nr:04d}'
        template_file_id = '{file_group}_{page_nr:04d}'
        for image in self.images:
            page_id, page_nr = self.document.get_unused_page_id(template_page_id)
            file_id = template_file_id.format(**{'page_nr': page_nr, 'file_group': file_group})
            self.document.add_image(image, page_id, file_id)
        self.images = []
        self.update_ui()

    def on_insert(self, _action: Gio.SimpleAction, _param):
        file_group = DEFAULT_FILE_GROUP
        template_page_id = 'PAGE_{page_nr:04d}'
        template_file_id = '{file_group}_{page_nr:04d}'
        page_ids = self.document.page_ids
        inserted_page_ids = []
        for image in self.images:
            page_id, page_nr = self.document.get_unused_page_id(template_page_id)
            file_id = template_file_id.format(**{'page_nr': page_nr, 'file_group': file_group})
            self.document.add_image(image, page_id, file_id)
            inserted_page_ids.append(page_id)

        index = page_ids.index(self.page_id)
        new_page_order = page_ids[:index] + inserted_page_ids + page_ids[index:]
        self.document.reorder(new_page_order)
        self.document.save()

        self.images = []
        self.update_ui()

    def pages_selected(self, sender, page_ids: List[str]):
        self.selected_page_ids = page_ids
        self.update_ui()

    def update_ui(self):
        self.window.actions['insert'].set_enabled(self.images)
        self.window.actions['append'].set_enabled(self.images)

    @property
    def use_file_group(self):
        return 'OCR-D-IMG'

    def config_changed(self, name, value):
        super().config_changed(name, value)
        self.reload()

    def redraw(self):
        self.update_ui()
        if self.images:
            for image, preview in zip(self.images, self.previews):
                scaled = cv_scale(image, None, self.ui.preview_height)
                preview.set_from_pixbuf(cv_to_pixbuf(scaled))


@Gtk.Template(filename=resource_filename(__name__, 'scan.ui'))
class ScanUi(Gtk.Box):
    __gtype_name__ = 'ScanUi'

    preview_left: Gtk.Image = Gtk.Template.Child()
    preview_right: Gtk.Image = Gtk.Template.Child()

    def __init__(self, view, **kwargs):
        Gtk.Box.__init__(self, **kwargs)
        self.view = view
        self.preview_height = 10

    @Gtk.Template.Callback()
    def on_size_allocate(self, widget, rect: Gdk.Rectangle):
        if abs(self.preview_height - rect.height) > 4:
            self.preview_height = rect.height
            self.view.redraw()
