import gi
gi.require_version('Gtk','3.0')
from gi.repository import GObject, Gtk, GdkPixbuf

import threading
from ocrd_utils import pushd_popd
from ocrd_browser.image_util import pil_to_pixbuf
from ocrd_browser.model import Document


class LazyLoadingPixbufListStore(Gtk.ListStore):
    def __init__(self, types: tuple, pixbuf_column: int, pixbuf_callback,
                 loading_image_pixbuf: GdkPixbuf.Pixbuf = None):
        super().__init__(*types)
        self.pixbuf_column = pixbuf_column
        self.pixbuf_callback = pixbuf_callback
        self.loading = False

        if loading_image_pixbuf:
            self.loading_image_pixbuf = loading_image_pixbuf
        else:
            theme = Gtk.IconTheme.get_default()
            self.loading_image_pixbuf = theme.load_icon_for_scale('image-loading', Gtk.IconSize.LARGE_TOOLBAR, 40, 0)

        self.connect('row-inserted', self.on_row_inserted)
        self.connect('row-changed', self.on_row_changed)

    def on_row_inserted(self, *_):
        self.reload()

    def on_row_changed(self, store, it, path):
        pass
        # print('change', store, it)
        # TODO: This will lead to recursion,
        # instead do something clever in reload like
        # storing a hash (or filename + last modified or ...) in one column and compare with current
        # store[it][self.pixbuf_column] = None
        # self.reload()

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
        text_renderer: Gtk.CellRendererText = \
        [cell for cell in self.get_cells() if isinstance(cell, Gtk.CellRendererText)][0]
        text_renderer.ellipsize = 'middle'
        self.model = self._setup_model()
        self.set_model(self.model)
        GLib.idle_add(self.model.reload)
        GLib.idle_add(self.goto_index, 0)

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
