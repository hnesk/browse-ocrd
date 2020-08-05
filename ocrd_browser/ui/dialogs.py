from gi.repository import Gtk, GdkPixbuf
from pkg_resources import resource_filename
from ocrd_browser import __version__


@Gtk.Template(filename=resource_filename(__name__, '../resources/about-dialog.ui'))
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self, **kwargs):
        Gtk.AboutDialog.__init__(self, **kwargs)
        self.set_logo(GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/logo.png'))
        self.set_version(__version__)


@Gtk.Template(filename=resource_filename(__name__, '../resources/open-dialog.ui'))
class OpenDialog(Gtk.FileChooserDialog):
    __gtype_name__ = "OpenDialog"

    def __init__(self, **kwargs):
        Gtk.FileChooserDialog.__init__(self, **kwargs)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("METS files")
        filter_text.add_mime_type("text/xml")
        self.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        self.add_filter(filter_any)
