from gi.repository import Gtk
from ocrd_browser.view import View

class ViewScan(View):
    """
    Imports book pages from reality
    """

    label = 'Scan'

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.label: Gtk.Label = None

    def build(self):
        super().build()
        hbox = Gtk.Box(visible=True)
        self.viewport.add(hbox)

    @property
    def use_file_group(self):
        return 'OCR-D-IMG'

    def config_changed(self, name, value):
        super().config_changed(name, value)
        self.reload()

    def redraw(self):
        if self.current:
            self.label.set_label(self.current.file.local_filename)



