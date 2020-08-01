import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
from pkg_resources import resource_filename
from ocrd_browser.image_util import pil_to_pixbuf, pil_scale
from .base import View


@Gtk.Template(filename=resource_filename(__name__, '../resources/view-images.ui'))
class ViewImages(Gtk.Box, View):
    __gtype_name__ = "ViewImages"

    file_group: str = GObject.Property(type=str, default='OCR-D-IMG')
    page_qty: int = GObject.Property(type=int, default=1)

    image_box: Gtk.Box = Gtk.Template.Child()
    file_group_selector: Gtk.ComboBox = Gtk.Template.Child()
    page_qty_selector: Gtk.SpinButton = Gtk.Template.Child()
    view_action_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        Gtk.Box.__init__(self)
        View.__init__(self, **kwargs)
        self.preview_height = 10
        self.pages = []
        self.page_id = None
        self.rebuild_images()

        self.bind_property('page_qty', self.page_qty_selector, 'value', GObject.BindingFlags.BIDIRECTIONAL)
        self.connect('notify::page-qty', lambda *args: self.rebuild_images())
        self.bind_property('file_group', self.file_group_selector, 'active_id', GObject.BindingFlags.BIDIRECTIONAL)
        self.connect('notify::file-group', lambda *args: self.reload())

    def setup(self):
        if not self.document.empty:
            self.setup_file_group_selector(self.file_group_selector, 'image')
        self.setup_close_button(self.view_action_box)

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

    def reload(self):
        try:
            index = self.document.page_ids.index(self.page_id)
        except ValueError:
            return
        index = index - index % self.page_qty
        display_ids = self.document.page_ids[index:index + self.page_qty]
        self.pages = []
        for display_id in display_ids:
            self.pages.append(self.document.page_for_id(display_id, self.file_group))
        self.redraw()

    @Gtk.Template.Callback()
    def on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle):
        if abs(self.preview_height - rect.height) > 4:
            self.preview_height = rect.height
            self.redraw()

    def redraw(self):
        if self.pages:
            for image, page in zip(self.image_box.get_children(), self.pages):
                thumbnail = pil_scale(page.image, None, self.preview_height - 10)
                image.set_from_pixbuf(pil_to_pixbuf(thumbnail))
