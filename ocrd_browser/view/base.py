from gi.repository import Gtk, Pango, GObject, Gdk
from enum import Enum
from typing import List, Tuple, Any
from ocrd_utils.constants import MIMETYPE_PAGE, MIME_TO_EXT
from ocrd_browser.model import Document, Page


class Configurator(Gtk.Widget):
    def __init__(self):
        self.document = None
        self.value = None

    def set_document(self, document: Document):
        self.document = document

    def set_value(self, value):
        raise NotImplementedError('You have to override set_value')


class View:
    def __init__(self, name: str, window: Gtk.Window):
        self.name: str = name
        self.window: Gtk.Window = window
        self.document: Document = None
        self.current: Page = None
        self.page_id: str = None

        self.configurators: List[Tuple[str, Configurator]] = []
        self.container: Gtk.Box = None
        self.action_bar: Gtk.ActionBar = None
        self.viewport: Gtk.Viewport = None

    def build(self):
        self.container = Gtk.Box(visible=True, orientation="vertical")
        self.action_bar = Gtk.ActionBar(visible=True)
        self.action_bar.pack_end(CloseButton(self.name))

        scroller = Gtk.ScrolledWindow(visible=True, shadow_type='in', propagate_natural_width=True)
        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        self.viewport.connect('size-allocate', self.on_viewport_size_allocate)
        scroller.add(self.viewport)

        self.container.pack_start(self.action_bar, False, True, 0)
        self.container.pack_start(scroller, True, True, 0)

    def set_document(self, document: Document):
        self.document = document
        for (_name, configurator) in self.configurators:
            configurator.set_document(document)

    def add_configurator(self, name: str, configurator: Configurator) -> None:
        """
        Adds a configurator for property self.{name}

        @param name: str
        @param configurator: Configurator|Gtk.Widget
        """
        if not hasattr(self, name):
            raise AttributeError(f'{self.__class__.__name__} has no attribute {name}.')
        configurator.set_value(getattr(self, name))
        self.configurators.append((name, configurator))
        configurator.connect('changed', lambda _source, *value: self.config_changed(name, value))
        self.action_bar.pack_start(configurator)

    def config_changed(self, name: str, value: Any) -> None:
        if len(value) == 1:
            value = value[0]
        setattr(self, name, value)

    @property
    def use_file_group(self) -> str:
        return 'OCR-D-IMG'

    def page_activated(self, sender, page_id):
        self.page_id = page_id
        self.reload()

    def pages_selected(self, _sender: Gtk.Widget, page_ids: List[str]) -> None:
        pass

    def reload(self):
        self.current = self.document.page_for_id(self.page_id, self.use_file_group)
        self.redraw()

    def redraw(self):
        pass

    def on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle):
        self.on_size(rect.width, rect.height, rect.x, rect.y)

    def on_size(self, w, h, x, y):
        pass


class PageQtySelector(Gtk.Box, Configurator):

    def __init__(self):
        super().__init__(visible=True, spacing=3)
        self.value = None

        label = Gtk.Label(label='# Pages:', visible=True)

        self.pages = Gtk.SpinButton(visible=True, max_length=2, width_chars=2, max_width_chars=2, numeric=True)
        self.pages.set_tooltip_text('How many pages should be displayed at once?')
        self.pages.set_adjustment(Gtk.Adjustment.new(1, 1, 16, 1, 4, 3))

        self.pack_start(label, False, True, 0)
        self.pack_start(self.pages, False, True, 0)

        self.pages.connect('value-changed', self.value_changed)

    def set_value(self, value):
        self.value = value
        self.pages.set_value(value)

    def value_changed(self, spin: Gtk.SpinButton):
        self.emit('changed', int(spin.get_value()))

    @GObject.Signal(arg_types=(int,))
    def changed(self, page_qty: int):
        self.value = page_qty


class FileGroupSelector(Gtk.Box, Configurator):

    def __init__(self, filter_=None, show_mime=False, show_ext=True):
        super().__init__(visible=True, spacing=3)
        self.value = None
        label = Gtk.Label(label='Group:', visible=True)

        self.groups = FileGroupComboBox(filter_, show_mime, show_ext)

        self.pack_start(label, False, True, 0)
        self.pack_start(self.groups, False, True, 0)

        self.groups.connect('changed', self.combo_box_changed)

    def set_value(self, value):
        self.value = value
        active_id = None
        for id_, group, mime, _ext in self.groups.get_model():
            if (value[0] is None or value[0] == group) and (value[1] is None or value[1] == mime):
                active_id = id_
                break
        if active_id:
            self.groups.set_active_id(active_id)

    def set_document(self, document: Document):
        self.groups.set_document(document)
        self.set_value(self.value)

    def combo_box_changed(self, combo: Gtk.ComboBox):
        model = combo.get_model()
        if len(model) > 0:
            row = combo.get_model()[combo.get_active()][:]
            self.emit('changed', row[FileGroupComboBox.COLUMN_GROUP], row[FileGroupComboBox.COLUMN_MIME])

    @GObject.Signal()
    def changed(self, file_group: str, mime_type: str):
        self.value = (file_group, mime_type)


class FileGroupComboBox(Gtk.ComboBox):
    COLUMN_ID = 0
    COLUMN_GROUP = 1
    COLUMN_MIME = 2
    COLUMN_EXT = 3

    def __init__(self, filter_=None, show_mime=False, show_ext=True):
        Gtk.ComboBox.__init__(self, visible=True)
        self.set_model(Gtk.ListStore(str, str, str, str))
        self.filter = filter_
        self.set_id_column(self.COLUMN_ID)

        self.add_renderer(self.COLUMN_GROUP, 120 if show_mime else 200)
        if show_mime:
            self.add_renderer(self.COLUMN_MIME, 80)
        if show_ext:
            self.add_renderer(self.COLUMN_EXT)

    def set_document(self, document: Document):
        self.set_model(FileGroupModel.build(document, self.filter))
        # self.set_active(0)

    def add_renderer(self, column, width=None):
        renderer = Gtk.CellRendererText()
        renderer.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        if width:
            renderer.props.width = width
        self.pack_start(renderer, False)
        self.add_attribute(renderer, "text", column)
        return renderer


class FileGroupModel(Gtk.ListStore):
    def __init__(self, document: Document):
        super().__init__(str, str, str, str)
        for group, mime in document.file_groups_and_mimetypes:
            self.append(('{}|{}'.format(group, mime), group, mime, MIME_TO_EXT.get(mime, '.???')))

    @classmethod
    def build(cls, document: Document, filter_: 'FileGroupFilter' = None) -> 'FileGroupModel':
        model = cls(document)
        model = model.filter_new()
        model.set_visible_func(filter_ if filter_ else FileGroupFilter.ALL)
        return model

    @staticmethod
    def image_filter(model, it, _data):
        return model[it][FileGroupComboBox.COLUMN_MIME].startswith('image/')

    @staticmethod
    def page_filter(model, it, _data):
        return model[it][FileGroupComboBox.COLUMN_MIME] == MIMETYPE_PAGE

    @staticmethod
    def all_filter(_model, _it, _data) -> bool:
        return True


class FileGroupFilter(Enum):
    IMAGE = FileGroupModel.image_filter
    PAGE = FileGroupModel.page_filter
    ALL = FileGroupModel.all_filter


class CloseButton(Gtk.Button):
    def __init__(self, view_name):
        Gtk.Button.__init__(self, visible=True)
        self.set_name('close_{}'.format(view_name))
        self.set_detailed_action_name('win.close_view("{}")'.format(view_name))
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_always_show_image(True)
        pixbuf = Gtk.IconTheme.get_default().load_icon('window-close', Gtk.IconSize.SMALL_TOOLBAR,
                                                       Gtk.IconLookupFlags.FORCE_SYMBOLIC)
        image = Gtk.Image(visible=True)
        image.set_from_pixbuf(pixbuf)
        self.set_image(image)
