import gi
gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, Gdk, GObject, GtkSource
from ocrd_models.ocrd_page import to_xml
from ocrd_browser.image_util import pil_to_pixbuf, pil_scale
from ocrd_browser.model import Document, Page

GObject.type_register(GtkSource.View)

class View:
    def __init__(self, file_group = None, document = None):
        self.document: Document = document
        self.current: Page = None
        self.file_group = file_group

    def set_document(self, document: Document):
        self.document: Document = document
        self.current = None

    def page_activated(self, sender, page_id):
        self.current = self.document.page_for_id(page_id, self.file_group)
        self.redraw()

    def redraw(self):
        pass


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/view-single.ui")
class ViewSingle(Gtk.ScrolledWindow,View):
    __gtype_name__ = "ViewSingle"

    image: Gtk.Image = Gtk.Template.Child()

    def __init__(self, **kwargs):
        Gtk.ScrolledWindow.__init__(self)
        View.__init__(self, **kwargs)
        self.preview_height = 0

    @Gtk.Template.Callback()
    def on_image_size(self, sender:Gtk.Widget, rect: Gdk.Rectangle):
        if abs(self.preview_height - rect.height) > 4:
            self.preview_height = rect.height
            self.redraw()

    def redraw(self):
        if self.current:
            thumbnail = pil_scale(self.current.image, None, self.preview_height)
            self.image.set_from_pixbuf(pil_to_pixbuf(thumbnail))



@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/view-multi.ui")
class ViewMulti(Gtk.ScrolledWindow,View):
    __gtype_name__ = "ViewMulti"

    image_template: Gtk.Image = Gtk.Template.Child()
    box: Gtk.Box = Gtk.Template.Child()


    def __init__(self, image_count=2, **kwargs):
        Gtk.ScrolledWindow.__init__(self)
        View.__init__(self, **kwargs)
        self.image_count = image_count
        self.preview_height = 300
        self.images = []
        self.pages = []

        box_properties = {}
        for key in self.box.list_child_properties():
            box_properties[key.name] = self.box.child_get_property(self.image_template, key.name)

        image_properties = {}
        for key in self.image_template.list_properties():
            image_properties[key.name] = self.image_template.get_property(key.name)
        image_properties.pop('parent', None)

        self.box.remove(self.image_template)

        for i in range(0,self.image_count):
            image = Gtk.Image()
            image.set_properties(image_properties)
            image.set_visible(True)
            for name, value in box_properties.items():
                self.box.child_set_property(image, name, value)
            self.images.append(image)
            self.box.add(image)


    @Gtk.Template.Callback()
    def on_image_size(self, sender:Gtk.Widget, rect: Gdk.Rectangle):
        if self.preview_height > 30 and abs(self.preview_height - rect.height) > 4:
            self.preview_height = rect.height
            self.redraw()

    def page_activated(self, sender, page_id):
        try:
            index = self.document.page_ids.index(page_id)
        except ValueError:
            return
        index = index - index % self.image_count
        display_ids = self.document.page_ids[index:index+self.image_count]
        self.pages = []
        for display_id in display_ids:
            self.pages.append(self.document.page_for_id(display_id, self.file_group))
        self.redraw()


    def redraw(self):
        if self.pages:
            for image, page in zip(self.images, self.pages):
                thumbnail = pil_scale(page.image, None, self.preview_height - 10)
                image.set_from_pixbuf(pil_to_pixbuf(thumbnail))



@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/view-xml.ui")
class ViewXml(Gtk.ScrolledWindow,View):
    __gtype_name__ = "ViewXml"

    text_view: GtkSource.View = Gtk.Template.Child()

    def __init__(self, **kwargs):
        Gtk.ScrolledWindow.__init__(self)
        View.__init__(self, **kwargs)
        lang_manager = GtkSource.LanguageManager()
        style_manager = GtkSource.StyleSchemeManager()
        self.buffer: GtkSource.Buffer = self.text_view.get_buffer()
        self.buffer.set_language(lang_manager.get_language('xml'))
        self.buffer.set_style_scheme(style_manager.get_scheme('tango'))


    def redraw(self):
        if self.current:
            self.buffer.set_text(to_xml(self.current.pcGts))

