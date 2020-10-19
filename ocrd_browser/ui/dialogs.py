from gi.repository import Gtk, GdkPixbuf
from typing import Any
from pkg_resources import resource_filename
from ocrd_browser import __version__
from ocrd_browser.model import Document


@Gtk.Template(filename=resource_filename(__name__, '../resources/about-dialog.ui'))
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self, **kwargs: Any):
        Gtk.AboutDialog.__init__(self, **kwargs)
        # noinspection PyCallByClass,PyArgumentList
        self.set_logo(GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/logo.png'))
        self.set_version(__version__)


@Gtk.Template(filename=resource_filename(__name__, '../resources/open-dialog.ui'))
class OpenDialog(Gtk.FileChooserDialog):
    __gtype_name__ = "OpenDialog"

    def __init__(self, **kwargs: Any):
        # noinspection PyCallByClass
        Gtk.FileChooserDialog.__init__(self, **kwargs)

        filter_mets = Gtk.FileFilter()
        filter_mets.set_name("METS files")
        filter_mets.add_mime_type("application/mets+xml")
        filter_mets.add_pattern("*.xml")
        self.add_filter(filter_mets)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        self.add_filter(filter_any)


@Gtk.Template(filename=resource_filename(__name__, '../resources/save-dialog.ui'))
class SaveDialog(Gtk.FileChooserDialog):
    __gtype_name__ = "SaveDialog"

    def __init__(self, **kwargs: Any):
        # noinspection PyCallByClass
        Gtk.FileChooserDialog.__init__(self, **kwargs)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("METS files")
        filter_text.add_mime_type("text/xml")
        self.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        self.add_filter(filter_any)


class SaveChangesDialog(Gtk.MessageDialog):

    def __init__(self, document: Document, **kwargs: Any):
        Gtk.MessageDialog.__init__(self, **kwargs)
        name = document.workspace.mets.unique_identifier if document.workspace.mets.unique_identifier else '<unnamed>'
        self.props.text = 'Save changes to document "{}" before closing?'.format(name)
        self.props.secondary_text = 'If you don’t save, changes to {} will be permanently lost.'.format(
            document.original_url if document.original_url else 'this file')
        self.props.message_type = Gtk.MessageType.QUESTION

        # Close Button
        close_button: Gtk.Button = self.add_button('Close without saving', Gtk.ResponseType.NO)
        close_button.get_style_context().add_class('destructive-action')

        # Cancel Button
        self.add_button('_Cancel', Gtk.ResponseType.CANCEL)

        # Save Button
        save_text = '_Save' if document.original_url else '_Save as ...'
        save_button: Gtk.Button = self.add_button(save_text, Gtk.ResponseType.YES)

        self.set_default(save_button)
