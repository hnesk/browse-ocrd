import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, Gio, GObject, GLib
from ocrd_utils import pushd_popd
from ocrd_browser import __version__
from ocrd_browser.image_util import pil_to_pixbuf
from ocrd_browser.model import Document
from ocrd_browser.views import ViewSingle, ViewXml, ViewMulti

import threading


class ActionRegistry:

    def __init__(self):
        self.actions = {}

    def create_simple_action(self, name, callback=None):
        callback = callback if callback else getattr(self, 'on_' + name)
        action: Gio.SimpleAction = Gio.SimpleAction.new(name)
        action.connect("activate", callback)
        self.add_action(action)
        self.actions[name] = action
        return action

@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/mainwindow.ui")
class MainWindow(Gtk.ApplicationWindow, ActionRegistry):
    __gtype_name__ = "MainWindow"

    headerbar: Gtk.HeaderBar = Gtk.Template.Child()
    page_list_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()
    panes: Gtk.Paned = Gtk.Template.Child()
    current_page_label: Gtk.Label = Gtk.Template.Child()


    def __init__(self, file = None, **kwargs):
        Gtk.ApplicationWindow.__init__(self, **kwargs)
        ActionRegistry.__init__(self)
        self.views = []
        self.current_page_id = None
        self.create_simple_action('close')
        self.create_simple_action('goto_first')
        self.create_simple_action('go_back')
        self.create_simple_action('go_forward')
        self.create_simple_action('goto_last')

        self.document = Document.load(file)

        title = self.document.workspace.mets.unique_identifier if self.document.workspace.mets.unique_identifier else '<Unbenannt>'

        self.set_title(title)
        self.headerbar.set_title(title)
        self.headerbar.set_subtitle(self.document.workspace.directory)

        self.page_list = PagePreviewList(self.document)
        self.page_list_scroller.add(self.page_list)
        self.page_list.connect('page_selected', self.page_selected)
        self.box = Gtk.Box()
        self.box.set_visible(True)
        self.box.set_homogeneous(True)
        self.panes.add(self.box)
        self.add_view(ViewSingle(file_group='OCR-D-IMG'))
        #self.add_view(ViewSingle(file_group='OCR-D-IMG-BIN'))
        #self.add_view(ViewMulti(file_group='OCR-D-IMG', image_count=2))
        #self.add_view(ViewXml(file_group='OCR-D-OCR-TESS-frk'))


        if len(self.document.page_ids):
            self.page_selected(None, self.document.page_ids[0])

    def add_view(self, view: 'View'):
        view.set_document(self.document)
        self.views.append(view)
        self.connect('page_activated', view.page_activated)
        self.box.pack_start(view, True, True,3)

    def page_selected(self, sender, page_id):
        if self.current_page_id != page_id:
            self.current_page_id = page_id
            self.emit('page_activated', page_id)

    @GObject.Signal(arg_types=(str,))
    def page_activated(self, page_id):
        index = self.document.page_ids.index(page_id)
        self.current_page_label.set_text('#{} ({}/{})'.format(page_id, index+1,len(self.document.page_ids)))
        self.update_ui()
        pass

    def update_ui(self):
        if self.current_page_id and len(self.document.page_ids)>0:
            index = self.document.page_ids.index(self.current_page_id)
            last_page = len(self.document.page_ids) - 1
            self.actions['goto_first'].set_enabled(index > 0)
            self.actions['go_back'].set_enabled(index > 0)
            self.actions['go_forward'].set_enabled(index < last_page)
            self.actions['goto_last'].set_enabled(index < last_page)

    def on_close(self, action: Gio.SimpleAction, _):
        self.destroy()

    def on_goto_first(self, action: Gio.SimpleAction, param):
        self.page_list.goto_index(0)

    def on_go_forward(self, action: Gio.SimpleAction, param):
        self.page_list.skip(1)

    def on_go_back(self, action: Gio.SimpleAction, param):
        self.page_list.skip(-1)

    def on_goto_last(self, action: Gio.SimpleAction, param):
        self.page_list.goto_index(-1)


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/about-dialog.ui")
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self, **kwargs):
        Gtk.AboutDialog.__init__(self, **kwargs)
        self.set_logo(GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/logo.png'))
        self.set_version(__version__)


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/open-dialog.ui")
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



class LazyLoadingPixbufListStore(Gtk.ListStore):
    def __init__(self, types: tuple, pixbuf_column: int, pixbuf_callback, loading_image_pixbuf: GdkPixbuf.Pixbuf = None):
        super().__init__(*types)
        self.pixbuf_column = pixbuf_column
        self.pixbuf_callback = pixbuf_callback
        self.loading = False

        if loading_image_pixbuf:
            self.loading_image_pixbuf = loading_image_pixbuf
        else:
            self.loading_image_pixbuf = Gtk.IconTheme.get_default().load_icon_for_scale('image-loading', Gtk.IconSize.LARGE_TOOLBAR, 40, 0)

        self.connect('row-inserted',self.on_row_inserted)
        self.connect('row-changed',self.on_row_changed)

    def on_row_inserted(self, *args):
        self.reload()

    def on_row_changed(self, store, iter, path):
        pass
        #print('change', store, iter)
        # TODO: This will lead to recursion,
        # instead do something clever in reload like
        # storing a hash (or filename + last modified or ...) in one column and compare with current
        #store[iter][self.pixbuf_column] = None
        #self.reload()

    def reload(self):
        for row in self:
            if row[self.pixbuf_column] is None:
                row[self.pixbuf_column] = self.loading_image_pixbuf

        if not self.loading:
            thread = threading.Thread(target=self.load_images)
            thread.start()

    def load_images(self):
        self.loading = True
        did_something = True
        while did_something:
            did_something = False
            for row in self:
                pixbuf = row[self.pixbuf_column]
                if pixbuf is None or pixbuf is self.loading_image_pixbuf:
                    did_something = self.pixbuf_callback(row)

        self.loading = False


@Gtk.Template(resource_path="/org/readmachine/ocrd-browser/ui/page-list.ui")
class PagePreviewList(Gtk.IconView):
    __gtype_name__ = "PagePreviewList"

    def __init__(self, document: Document, **kwargs):
        super().__init__(**kwargs)
        self.document = document
        self.current: Gtk.TreeIter = None
        self.set_text_column(0)
        self.set_tooltip_column(1)
        self.set_pixbuf_column(2)
        self.set_item_width(50)
        text_renderer: Gtk.CellRendererText = [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)][0]
        text_renderer.ellipsize = 'middle'
        self.model = self._setup_model()
        self.set_model(self.model)
        GLib.idle_add(self.model.reload)
        GLib.idle_add(self.goto_index,0)


    def goto_index(self, index):
        index = index if index >= 0 else len(self.model) + index
        if 0 <= index < len(self.model):
            self.goto_path(Gtk.TreePath(index))

    def skip(self, pos):
        iterate = self.model.iter_previous if pos < 0 else self.model.iter_next
        n = iterate(self.current)
        self.goto_path(self.model.get_path(n))

    def goto_path(self, path):
        self.unselect_all()
        self.select_path(path)
        self.set_cursor(path, None, False)
        self.emit('activate_cursor_item')


    def _setup_model(self):
        model = LazyLoadingPixbufListStore((str, str, GdkPixbuf.Pixbuf), 2, self.pixbuf_loader)
        for page_id in self.document.page_ids:
            model.append([page_id, 'Loading', None])
        return model

    def pixbuf_loader(self, row: Gtk.TreeModelRow):
        page_id = row[0]
        with pushd_popd(self.document.workspace.directory):
            page = self.document.page_for_id(page_id)
        thumb = page.image.copy()
        thumb.thumbnail((100, 500))
        row[1] = '{0} ({1}x{2})'.format(page.page.imageFilename, page.page.imageWidth, page.page.imageHeight)
        row[2] = pil_to_pixbuf(thumb)


    def do_item_activated(self, path: Gtk.TreePath):
        self.current = self.model.get_iter(path)
        self.emit('page_selected', self.model[path][0])

    @GObject.Signal()
    def page_selected(self, page_id: str):
        pass

