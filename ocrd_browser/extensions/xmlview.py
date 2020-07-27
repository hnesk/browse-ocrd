import gi

try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GObject, GtkSource
from ocrd_models.ocrd_page import to_xml
from ocrd_browser.views import View
from pkg_resources import resource_filename

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


@Gtk.Template(filename=resource_filename(__name__, 'resources/view-xml.ui'))
class ViewXml(Gtk.Box, View):
    """
    A view of the current Page-Xml with syntax highlighting via GtkSourceView
    """
    __gtype_name__ = "ViewXml"

    file_group: str = GObject.Property(type=str, default='OCR-D-IMG')

    view_action_box: Gtk.Box = Gtk.Template.Child()
    text_view: GtkSource.View = Gtk.Template.Child()
    file_group_selector: Gtk.ComboBoxText = Gtk.Template.Child()

    def __init__(self, **kwargs):
        Gtk.Box.__init__(self)
        View.__init__(self, **kwargs)
        self.buffer = self.setup_buffer()

        self.bind_property('file_group', self.file_group_selector, 'active_id', GObject.BindingFlags.BIDIRECTIONAL)
        self.connect('notify::file-group', lambda *args: self.reload())

    def setup(self):
        self.setup_file_group_selector(self.file_group_selector)
        self.setup_close_button(self.view_action_box)

    def setup_buffer(self) -> GtkSource.Buffer:
        lang_manager = GtkSource.LanguageManager()
        style_manager = GtkSource.StyleSchemeManager()
        buffer: GtkSource.Buffer = self.text_view.get_buffer()
        buffer.set_language(lang_manager.get_language('xml'))
        buffer.set_style_scheme(style_manager.get_scheme('tango'))
        return buffer

    def redraw(self):
        if self.current:
            self.buffer.set_text(to_xml(self.current.pc_gts))
            print(self.document.path(self.current.file))
