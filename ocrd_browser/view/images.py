from gi.repository import Gtk

from itertools import zip_longest
from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from .base import View, FileGroupSelector, FileGroupFilter, PageQtySelector


class ViewImages(View):
    """
    View of one or more consecutive images
    """

    label = 'Image'

    def __init__(self, name, window, **kwargs):
        super().__init__(name, window, **kwargs)
        self.file_group = ('OCR-D-IMG', None)
        self.page_qty = 1
        self.preview_height = 10
        self.image_box = None
        self.pages = []

    def build(self):
        super(ViewImages, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.IMAGE))
        self.add_configurator('page_qty', PageQtySelector())

        self.image_box = Gtk.Box(visible=True, homogeneous=True)
        self.viewport.add(self.image_box)
        self.rebuild_images()

    def config_changed(self, name, value):
        super(ViewImages, self).config_changed(name, value)
        if name == 'page_qty':
            self.rebuild_images()
        self.reload()

    def rebuild_images(self):
        existing_images = {child.get_name(): child for child in self.image_box.get_children()}

        for i in range(0, self.page_qty):
            name = 'image_{}'.format(i)
            if not existing_images.pop(name, None):
                image = Gtk.Image(name=name, visible=True, icon_name='gtk-missing-image', icon_size=Gtk.IconSize.DIALOG)
                self.image_box.add(image)

        for child in existing_images.values():
            child.destroy()

        self.reload()

    def page_activated(self, _sender, page_id):
        self.page_id = page_id
        self.reload()

    @property
    def use_file_group(self):
        return self.file_group[0]

    def reload(self):
        if self.document:
            display_ids = self.document.display_id_range(self.page_id, self.page_qty)
            self.pages = []
            for display_id in display_ids:
                self.pages.append(self.document.page_for_id(display_id, self.use_file_group))
        self.redraw()

    def on_size(self, _w, h, _x, _y):
        if abs(self.preview_height - h) > 4:
            self.preview_height = h
            self.redraw()

    def redraw(self):
        if self.pages:
            image: Gtk.Image
            for image, page in zip_longest(self.image_box.get_children(), self.pages):
                if page:
                    thumbnail = pil_scale(page.image, None, self.preview_height - 10)
                    image.set_from_pixbuf(pil_to_pixbuf(thumbnail))
                else:
                    image.set_from_stock('missing-image', Gtk.IconSize.DIALOG)
