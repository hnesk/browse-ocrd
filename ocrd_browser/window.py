from gi.repository import Gtk, GdkPixbuf, Gio, GObject, GLib, Pango, Gdk

from ocrd_browser import __version__
from ocrd_browser.model import Document, DEFAULT_FILE_GROUP
from ocrd_browser.view import ViewRegistry, ViewImages, View
from ocrd_browser.icon_store import LazyLoadingListStore
from ocrd_browser.image_util import cv_scale, cv_to_pixbuf
from ocrd_browser.gtk_util import ActionRegistry
from pkg_resources import resource_filename
from typing import List

import cv2
import os


@Gtk.Template(filename=resource_filename(__name__, 'resources/main-window.ui'))
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    page_list_scroller: Gtk.ScrolledWindow = Gtk.Template.Child()
    panes: Gtk.Paned = Gtk.Template.Child()
    current_page_label: Gtk.Label = Gtk.Template.Child()
    view_container: Gtk.Box = Gtk.Template.Child()
    view_menu_box: Gtk.Box = Gtk.Template.Child()


    def __init__(self, **kwargs):
        Gtk.ApplicationWindow.__init__(self, **kwargs)
        self.set_icon(GdkPixbuf.Pixbuf.new_from_resource("/org/readmachine/ocrd-browser/icons/icon.png"))
        self.views = []
        self.current_page_id = None
        self.document = Document.create(self)

        vstring = GLib.Variant("s", "")

        self.actions = ActionRegistry(for_widget=self)
        self.actions.create('close')
        self.actions.create('goto_first')
        self.actions.create('go_back')
        self.actions.create('go_forward')
        self.actions.create('goto_last')
        self.actions.create('page_remove')
        self.actions.create('page_properties')
        self.actions.create('close_view', param_type=vstring)
        self.actions.create('create_view', param_type=vstring)

        self.page_list = PagePreviewList(self.document)
        self.page_list_scroller.add(self.page_list)
        self.page_list.connect('page_selected', self.page_selected)

        for id_, view in self.view_registry.get_view_options().items():
            menu_item = Gtk.ModelButton(visible=True,centered=False,halign=Gtk.Align.FILL,label = view, hexpand=True)
            menu_item.set_detailed_action_name('win.create_view("{}")'.format(id_))
            self.view_menu_box.pack_start(menu_item, True, True, 0)

        self.add_view(ViewImages)

        self.update_ui()

    def on_page_remove(self, _a: Gio.SimpleAction, _p):
        for page_id in self.page_list.get_selected_ids():
            self.document.delete_page(page_id)

    def on_page_properties(self, _a: Gio.SimpleAction, _p):
        print(self.page_list.get_selected_items())


    @Gtk.Template.Callback()
    def on_recent_menu_item_activated(self, recent_chooser: Gtk.RecentChooserMenu):
        app = self.get_application()
        item: Gtk.RecentInfo = recent_chooser.get_current_item()
        app.open_in_window(item.get_uri(), window=self)


    def open(self, uri):
        self.set_title('Loading')
        self.header_bar.set_title('Loading ...')
        self.header_bar.set_subtitle(uri)
        self.update_ui()
        # Give GTK some break to show the Loading message
        GLib.timeout_add(50, self._open, uri)

    def _open(self, uri):
        self.document = Document.load(self,uri)
        self.page_list.set_document(self.document)

        title = self.document.workspace.mets.unique_identifier if self.document.workspace.mets.unique_identifier else '<unnamed>'
        self.set_title(title)
        self.header_bar.set_title(title)
        self.header_bar.set_subtitle(self.document.workspace.directory)

        for view in self.views:
            view.set_document(self.document)

        if len(self.document.page_ids):
            self.page_selected(None, self.document.page_ids[0])

    @property
    def view_registry(self) -> ViewRegistry:
        return self.get_application().view_registry

    def add_view(self, view_class):
        name = 'view_{}'.format(len(self.views))
        view: View = view_class(name, self)
        view.build()
        view.set_document(self.document)
        self.views.append(view)
        self.connect('page_activated', view.page_activated)
        self.view_container.pack_start(view.container, True, True, 3)

    def page_selected(self, _, page_id):
        if self.current_page_id != page_id:
            self.current_page_id = page_id
            self.emit('page_activated', page_id)

    @GObject.Signal(arg_types=(str,))
    def page_activated(self, page_id):
        index = self.document.page_ids.index(page_id)
        self.current_page_label.set_text('{}/{}'.format(index + 1, len(self.document.page_ids)))
        self.update_ui()
        pass

    @GObject.Signal(arg_types=(object,))
    def document_changed(self, page_ids: List):
        print(page_ids)
        self.page_list.document_changed(page_ids)

    @GObject.Signal()
    def document_saved(self):
        print('saved')


    def update_ui(self):
        can_go_back = False
        can_go_forward = False
        if self.current_page_id and len(self.document.page_ids) > 0:
            index = self.document.page_ids.index(self.current_page_id)
            last_page = len(self.document.page_ids) - 1
            can_go_back = index > 0
            can_go_forward = index < last_page

        self.actions['goto_first'].set_enabled(can_go_back)
        self.actions['go_back'].set_enabled(can_go_back)
        self.actions['go_forward'].set_enabled(can_go_forward)
        self.actions['goto_last'].set_enabled(can_go_forward)

    def on_close(self, _a: Gio.SimpleAction, _p):
        self.destroy()

    def on_goto_first(self, _a: Gio.SimpleAction, _p):
        self.page_list.goto_index(0)

    def on_go_forward(self, _a: Gio.SimpleAction, _p):
        self.page_list.skip(1)

    def on_go_back(self, _a: Gio.SimpleAction, _p):
        self.page_list.skip(-1)

    def on_goto_last(self, _a: Gio.SimpleAction, _p):
        self.page_list.goto_index(-1)

    def on_create_view(self, _a, selected_view_id: GLib.Variant):
        view_class = self.view_registry.get_view(selected_view_id.get_string())
        if view_class:
            self.add_view(view_class)

    def on_close_view(self, _action: Gio.SimpleAction, view_name: GLib.Variant):
        for view in self.views:
            if view.name == view_name.get_string():
                view.container.destroy()
                break
        self.disconnect_by_func(view.page_activated)
        self.views.remove(view)
        del view


@Gtk.Template(filename=resource_filename(__name__, 'resources/about-dialog.ui'))
class AboutDialog(Gtk.AboutDialog):
    __gtype_name__ = "AboutDialog"

    def __init__(self, **kwargs):
        Gtk.AboutDialog.__init__(self, **kwargs)
        self.set_logo(GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/logo.png'))
        self.set_version(__version__)


@Gtk.Template(filename=resource_filename(__name__, 'resources/open-dialog.ui'))
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


@Gtk.Template(filename=resource_filename(__name__, 'resources/page-list.ui'))
class PagePreviewList(Gtk.IconView):
    __gtype_name__ = "PagePreviewList"

    def __init__(self, document: Document, **kwargs):
        super().__init__(**kwargs)
        self.document: Document = None
        self.current: Gtk.TreeIter = None
        self.model: LazyLoadingListStore = None
        self.loading_image_pixbuf: GdkPixbuf.Pixbuf = None
        self.file_lookup: dict = None
        self.setup_ui()
        self.setup_context_menu()
        self.set_document(document)

    def setup_context_menu(self):
        menu = Gio.Menu()
        action_menu = Gio.Menu()
        action_menu.append('Remove', 'win.page_remove')
        menu.append_section(None, action_menu)
        prop_menu = Gio.Menu()
        prop_menu.append('Properties', 'win.page_properties')
        menu.append_section(None, prop_menu)
        self.cmenu: Gtk.Menu = Gtk.Menu()
        self.cmenu.bind_model(menu, None, True)
        self.cmenu.attach_to_widget(self)
        self.cmenu.show_all()

    def set_document(self, document):
        self.document = document
        self.setup_model()

    def document_changed(self, page_ids: List):
        to_delete = []
        for n,row in enumerate(self.model):
            if row[0] in page_ids:
                page_ids.remove(row[0])
                files = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=row[0])
                if files:
                    file_name = str(self.document.path(files[0].local_filename))
                    row[2] = file_name
                else:
                    to_delete.append(n)

        for delete in reversed(to_delete):
            self.model.remove(self.model.get_iter(Gtk.TreePath(delete)))

        for page_id in page_ids:
            file = self.document.workspace.mets.find_files(fileGrp=DEFAULT_FILE_GROUP, pageId=page_id)[0]
            file_name = str(self.document.path(file.local_filename))
            self.model.append((page_id, '', file_name, None))




    def setup_ui(self):
        self.loading_image_pixbuf = GdkPixbuf.Pixbuf.new_from_resource('/org/readmachine/ocrd-browser/icons/loading.png')
        self.set_text_column(0)
        self.set_tooltip_column(1)
        self.set_pixbuf_column(3)
        text_renderer: Gtk.CellRendererText = \
            [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)][0]
        text_renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.connect('button-release-event', self.button_pressed)

    def button_pressed(self, _sender, event: Gdk.EventButton):
        if event.get_button()[1] == 3:
            path, renderer = self.get_item_at_pos(*event.get_coords())
            row = self.model[path]
            self.emit('on_context_menu', event, row, path, renderer)

    @GObject.Signal(arg_types=(object, object, object, object))
    def on_context_menu(self, event: Gdk.EventButton, row: Gtk.TreeModelRow, path: Gtk.TreePath, renderer: Gtk.CellRenderer):
        if len(self.get_selected_items()) <= 1:
            self.set_cursor(path, None, False)
            self.emit('select_cursor_item')
        self.cmenu.popup_at_pointer(event)


    def setup_model(self):
        self.file_lookup = self.get_image_paths(self.document)
        self.model = LazyLoadingListStore(str, str, str, GdkPixbuf.Pixbuf,
                                          init_row=self.init_row, load_row=self.load_row, hash_row=self.hash_row)
        for page_id in self.document.page_ids:
            file = str(self.file_lookup[page_id])
            self.model.append((page_id, '', file, None))
        self.set_model(self.model)
        GLib.timeout_add(10, self.model.start_loading)

    def init_row(self, row: Gtk.TreeModelRow):
        row[1] = 'Loading {}'.format(row[2])
        row[3] = self.loading_image_pixbuf

    @staticmethod
    def load_row(row):
        image = cv2.imread(row[2])
        row[1] = '{} ({}x{})'.format(row[2], image.shape[1], image.shape[0])
        row[3] = cv_to_pixbuf(cv_scale(image, 100, None))
        return row

    @staticmethod
    def hash_row(row: Gtk.TreeModelRow):
        file = row[2]
        mtime = os.path.getmtime(file)
        return '{}:{}'.format(file, mtime)

    @staticmethod
    def get_image_paths(document: Document, file_group='OCR-D-IMG'):
        images = document.workspace.mets.find_files(fileGrp=file_group)
        page_ids = document.workspace.mets.get_physical_pages(for_fileIds=[image.ID for image in images])
        file_paths = [document.path(image.url) for image in images]
        return dict(zip(page_ids, file_paths))

    def get_selected_ids(self):
        return [self.model[path][0] for path in self.get_selected_items()]

    def goto_index(self, index):
        index = index if index >= 0 else len(self.model) + index
        if 0 <= index < len(self.model):
            self.goto_path(Gtk.TreePath(index))

    def skip(self, pos):
        if not self.current:
            self.current = self.model.get_iter(Gtk.TreePath(0))
        iterate = self.model.iter_previous if pos < 0 else self.model.iter_next
        n = iterate(self.current)
        self.goto_path(self.model.get_path(n))

    def goto_path(self, path):
        self.set_cursor(path, None, False)
        self.emit('select_cursor_item')
        self.emit('activate_cursor_item')
        self.grab_focus()

    def do_item_activated(self, path: Gtk.TreePath):
        self.current = self.model.get_iter(path)
        self.emit('page_selected', self.model[path][0])

    @GObject.Signal()
    def page_selected(self, page_id: str):
        pass
