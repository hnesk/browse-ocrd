import cv2
from gi.repository import Gtk, Gdk
from pkg_resources import resource_filename
from voussoir.pagewarper import PageWarper

from ocrd_browser.extensions.physical_import.scandriver import DummyDriver, AndroidADBDriver
from ocrd_browser.image_util import cv_scale, cv_to_pixbuf
from ocrd_browser.view import View


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

    def build(self):
        super().build()
        self.ui = ScanUi(self)
        self.previews = [self.ui.preview_left, self.ui.preview_right]
        self.viewport.add(self.ui)
        self.window.actions.create('scan', self.on_scan)

    def on_scan(self, *args):
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
            self.images =  []
            for n, layout in enumerate(self.layouts):
                self.images.append(pw.get_warped_image(layout, n == 1))
        except Exception as err:
            print('Warp: ' + str(err))

        self.redraw()

    @property
    def use_file_group(self):
        return 'OCR-D-IMG'

    def config_changed(self, name, value):
        super().config_changed(name, value)
        self.reload()

    def redraw(self):
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
