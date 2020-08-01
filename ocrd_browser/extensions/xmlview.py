import gi
gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')
from gi.repository import GObject, GtkSource

from ocrd_utils.constants import MIMETYPE_PAGE
from ocrd_models.ocrd_page import to_xml
from ocrd_browser.view import View
from ocrd_browser.view.base import FileGroupSelector, FileGroupFilter

GObject.type_register(GtkSource.View)


# Example for extension point 'ocrd_browser_ext'
#
# 'ocrd_browser_ext': [
#    'xml = ocrd_browser.extensions.xmlview:register',
# ],
#
# def on_xml(action, param):
#     print(action)
#
# def register(application: OcrdBrowserApplication):
#     application.get_app_menu().append('XML','app.xml')
#     application.create_simple_action('xml',on_xml)


# @Gtk.Template(filename=resource_filename(__name__, 'resources/view-xml.ui'))
class ViewXml(View):
    """
    A view of the current Page-Xml with syntax highlighting via GtkSourceView
    """

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.file_group = (None, MIMETYPE_PAGE)
        self.buffer = None

    def build(self):
        super(ViewXml, self).build()
        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))

        text_view = GtkSource.View(visible=True, vexpand=False, editable=False, monospace=True, show_line_numbers=True,
                                   width_request=400)
        self.buffer: GtkSource.Buffer = self.setup_buffer(text_view)
        self.viewport.add(text_view)

    @staticmethod
    def setup_buffer(text_view) -> GtkSource.Buffer:
        lang_manager = GtkSource.LanguageManager()
        style_manager = GtkSource.StyleSchemeManager()
        buffer: GtkSource.Buffer = text_view.get_buffer()
        buffer.set_language(lang_manager.get_language('xml'))
        buffer.set_style_scheme(style_manager.get_scheme('tango'))
        return buffer

    @property
    def use_file_group(self):
        return self.file_group[0]

    def config_changed(self, name, value):
        super().config_changed(name, value)
        self.reload()

    def redraw(self):
        if self.current:
            self.buffer.set_text(to_xml(self.current.pc_gts))
