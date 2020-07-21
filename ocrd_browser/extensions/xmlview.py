import gi
from gi.overrides import Gio

from ocrd_browser.application import OcrdBrowserApplication

try:
    gi.require_version('GtkSource', '4')
except ValueError:
    gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk, GObject, GtkSource, Gio
from ocrd_models.ocrd_page import to_xml
from ocrd_browser.views import View

GObject.type_register(GtkSource.View)

def on_xml(action, param):
    print(action)

def register(application: OcrdBrowserApplication):
    application.get_app_menu().append('XML','app.xml')
    application.create_simple_action('xml',on_xml)



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

