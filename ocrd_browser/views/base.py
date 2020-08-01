import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango
from typing import Optional
from ocrd_utils.constants import MIMETYPE_PAGE
from ocrd_browser.model import Document, Page


class View:
    def __init__(self, file_group=None, document=None):
        self.document: Document = document
        self.current: Optional[Page] = None
        self.file_group = file_group
        self.close_button = None
        self.page_id = None

    def setup(self):
        pass

    def set_document(self, document: Document):
        self.document: Document = document
        self.current = None

    def page_activated(self, sender, page_id):
        self.page_id = page_id
        self.reload()

    def reload(self):
        self.current = self.document.page_for_id(self.page_id, self.file_group)
        self.redraw()

    def setup_close_button(self, view_action_box: Gtk.Box):
        if self.close_button is None:
            self.close_button: Gtk.Button = Gtk.Button.new_from_icon_name('window-close', Gtk.IconSize.SMALL_TOOLBAR)
            self.close_button.set_name('close_button')
            self.close_button.set_visible(True)
            self.close_button.set_relief(Gtk.ReliefStyle.NONE)
            self.close_button.set_always_show_image(True)
            self.close_button.set_detailed_action_name('win.close_view("{}")'.format(self.get_name()))
            view_action_box.pack_end(self.close_button, False, False, 6)

    def image_filter(self, model, iter, _data):
        return model[iter][2].startswith('image/')

    def page_filter(self, model, iter, _data):
        v = model[iter][2]
        return v == MIMETYPE_PAGE

    def setup_file_group_selector(self, file_group_selector: Gtk.ComboBox, filter_=None):
        if file_group_selector.get_model() is None:
            model = self.document.file_group_model
            if filter_ is not None:
                model: Gtk.TreeModel = model.filter_new()
                if filter_ == 'image':
                    model.set_visible_func(self.image_filter)
                elif filter_ == 'page':
                    model.set_visible_func(self.page_filter)

            file_group_selector.set_model(model)
            file_group_selector.set_id_column(1)
            renderer_text = Gtk.CellRendererText()
            renderer_text.props.width = 150
            renderer_text.props.ellipsize = Pango.EllipsizeMode.MIDDLE
            file_group_selector.pack_start(renderer_text, False)
            file_group_selector.add_attribute(renderer_text, "text", 1)
            renderer_ext = Gtk.CellRendererText()
            file_group_selector.pack_start(renderer_ext, False)
            file_group_selector.add_attribute(renderer_ext, "text", 3)
            file_group_selector.set_active_id('OCR-D-IMG')

    def redraw(self):
        pass
