from gi.repository import Gtk, Pango, GObject, Gdk

from typing import List, Tuple, Any, Optional, Dict

from enum import Enum
from ocrd_utils.constants import MIMETYPE_PAGE, MIME_TO_EXT
from ocrd_browser.model import Document, Page


class Configurator(Gtk.Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.document: Optional[Document] = None
        self.value: Any = None

    def set_document(self, document: Document) -> None:
        self.document = document

    def set_value(self, value: Any) -> None:
        raise NotImplementedError('You have to override set_value')


class View:
    # noinspection PyTypeChecker
    def __init__(self, name: str, window: Gtk.Window):
        self.name: str = name
        self.window: Gtk.Window = window
        self.document: Document = None
        self.current: Page = None
        self.page_id: str = None

        self.configurators: Dict[str, Configurator] = {}
        self.container: Gtk.Box = None
        self.action_bar: Gtk.ActionBar = None
        self.scroller: Gtk.ScrolledWindow = None

    def build(self) -> None:
        self.container = Gtk.Box(visible=True, orientation="vertical")
        self.action_bar = Gtk.ActionBar(visible=True)
        self.action_bar.pack_end(CloseButton(self.name))

        self.scroller = Gtk.ScrolledWindow(visible=True, shadow_type='in', propagate_natural_width=True)

        self.container.pack_start(self.action_bar, False, True, 0)
        self.container.pack_start(self.scroller, True, True, 0)

    def set_document(self, document: Document) -> None:
        self.document = document
        for configurator in self.configurators.values():
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
        self.configurators[name] = configurator
        configurator.connect('changed', lambda _source, *value: self.config_changed(name, value))
        self.action_bar.pack_start(configurator)

    def config_changed(self, name: str, value: Any) -> None:
        if len(value) == 1:
            value = value[0]
        setattr(self, name, value)

    @property
    def use_file_group(self) -> str:
        return 'OCR-D-IMG'

    def page_activated(self, _sender: Gtk.Widget, page_id: str) -> None:
        self.page_id = page_id
        self.reload()

    def pages_selected(self, _sender: Gtk.Widget, page_ids: List[str]) -> None:
        pass

    def reload(self) -> None:
        self.current = self.document.page_for_id(self.page_id, self.use_file_group)
        self.redraw()

    def redraw(self) -> None:
        pass

    def update_ui(self) -> None:
        pass

    def on_size(self, w: int, h: int, x: int, y: int) -> None:
        pass


class PageQtySelector(Gtk.Box, Configurator):

    def __init__(self) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None

        label = Gtk.Label(label='#Pages:', visible=True)

        self.pages = Gtk.SpinButton(visible=True, max_length=2, width_chars=2, max_width_chars=2, numeric=True)
        self.pages.set_tooltip_text('How many pages should be displayed at once?')
        # noinspection PyCallByClass,PyArgumentList
        self.pages.set_adjustment(Gtk.Adjustment.new(1, 1, 16, 1, 0, 0))

        self.pack_start(label, False, True, 0)
        self.pack_start(self.pages, False, True, 0)

        self.pages.connect('value-changed', self.value_changed)

    def set_value(self, value: int) -> None:
        self.value = value
        self.pages.set_value(value)

    def value_changed(self, spin: Gtk.SpinButton) -> None:
        self.emit('changed', int(spin.get_value()))

    @GObject.Signal(arg_types=[int])
    def changed(self, page_qty: int) -> None:
        self.value = page_qty

class ImageZoomSelector(Gtk.Box, Configurator):

    def __init__(self, base:float = 2, step = 0.1, min_=-4.0, max_ = 4.0) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None

        label = Gtk.Label(label='Zoom:', visible=True)

        self.base = base
        self.scale = Gtk.SpinButton(visible=True, max_length=5, width_chars=5, max_width_chars=5, numeric=True, digits = 2)
        self.scale.set_tooltip_text('log{:+.2f} scale factor for viewing images'.format(base))
        # noinspection PyCallByClass,PyArgumentList
        self.scale.set_adjustment(Gtk.Adjustment.new(0.0, min_, max_, step, 0, 0))
        self.scale.set_snap_to_ticks(False)
        self.scale.connect('value-changed', self.value_changed)

        self.pack_start(label, False, True, 0)
        self.pack_start(self.scale, False, True, 0)

    def get_exp(self):
        return self.base ** self.value

    def set_value(self, value: float) -> None:
        adj: Gtk.Adjustment = self.scale.get_adjustment()
        value = min(adj.get_upper(), max(adj.get_lower(), value))
        self.scale.set_value(value)

    def value_changed(self, spin: Gtk.SpinButton) -> None:
        self.emit('changed', spin.get_value())
    
    @GObject.Signal(arg_types=[float])
    def changed(self, scale: float) -> None:
        self.value = scale
        self.scale.set_tooltip_text('{:.2%} / log{:.2f} scale factor for viewing images'.format(self.get_exp(), self.base))


class FileGroupSelector(Gtk.Box, Configurator):

    def __init__(self, filter_: Optional['FileGroupFilter'] = None, show_mime: bool = False, show_ext: bool = True):
        super().__init__(visible=True, spacing=3)
        self.value = None
        label = Gtk.Label(label='Group:', visible=True)

        self.groups = FileGroupComboBox(filter_, show_mime, show_ext)

        self.pack_start(label, False, True, 0)
        self.pack_start(self.groups, False, True, 0)

        self.groups.connect('changed', self.combo_box_changed)

    def set_value(self, value: Tuple[str, str]) -> None:
        self.value = value
        active_id = None
        for id_, group, mime, _ext in self.groups.get_model():
            if (value[0] is None or value[0] == group) and (value[1] is None or value[1] == mime):
                active_id = id_
                break
        if active_id:
            self.groups.set_active_id(active_id)

    def set_document(self, document: Document) -> None:
        self.groups.set_document(document)
        self.set_value(self.value)

    def combo_box_changed(self, combo: Gtk.ComboBox) -> None:
        model = combo.get_model()
        if len(model) > 0:
            row = combo.get_model()[combo.get_active()][:]
            self.emit('changed', row[FileGroupComboBox.COLUMN_GROUP], row[FileGroupComboBox.COLUMN_MIME])

    @GObject.Signal()
    def changed(self, file_group: str, mime_type: str) -> None:
        self.value = (file_group, mime_type)


class FileGroupComboBox(Gtk.ComboBox):
    COLUMN_ID = 0
    COLUMN_GROUP = 1
    COLUMN_MIME = 2
    COLUMN_EXT = 3

    def __init__(self, filter_: Optional['FileGroupFilter'] = None, show_mime: bool = False, show_ext: bool = True):
        Gtk.ComboBox.__init__(self, visible=True)
        self.set_model(Gtk.ListStore(str, str, str, str))
        self.filter = filter_
        self.set_id_column(self.COLUMN_ID)

        self.add_renderer(self.COLUMN_GROUP)
        if show_mime:
            self.add_renderer(self.COLUMN_MIME, 80)
        if show_ext:
            self.add_renderer(self.COLUMN_EXT)

        self.props.has_tooltip = True
        self.props.popup_fixed_width = False
        self.connect('query-tooltip', self.set_tooltip)

    def set_tooltip(self, _widget: Gtk.Widget, _x: int, _y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        model = self.get_model()
        if len(model) > 0:
            row = self.get_model()[self.get_active()][:]
            phs = {'fileGrp': row[self.COLUMN_GROUP], 'ext': row[self.COLUMN_EXT], 'mime': row[self.COLUMN_MIME]}
            tooltip.set_text('{fileGrp} (Mime-Type: {mime})'.format(**phs))
            return True
        return False

    def set_document(self, document: Document) -> None:
        self.set_model(FileGroupModel.build(document, self.filter))
        # self.set_active(0)

    def add_renderer(self, column: int, width: int = None) -> Gtk.CellRendererText:
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
    def image_filter(model: Gtk.TreeModel, it: Gtk.TreeIter, _data: None) -> bool:
        return str(model[it][FileGroupComboBox.COLUMN_MIME]).startswith('image/')

    @staticmethod
    def page_filter(model: Gtk.TreeModel, it: Gtk.TreeIter, _data: None) -> bool:
        # str casts for mypy
        return str(model[it][FileGroupComboBox.COLUMN_MIME]) == str(MIMETYPE_PAGE)

    @staticmethod
    def all_filter(_model: Gtk.TreeModel, _it: Gtk.TreeIter, _data: None) -> bool:
        return True


class FileGroupFilter(Enum):
    IMAGE = FileGroupModel.image_filter
    PAGE = FileGroupModel.page_filter
    ALL = FileGroupModel.all_filter


class CloseButton(Gtk.Button):
    def __init__(self, view_name: str):
        Gtk.Button.__init__(self, visible=True)
        self.set_name('close_{}'.format(view_name))
        self.set_detailed_action_name('win.close_view("{}")'.format(view_name))
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_always_show_image(True)
        # noinspection PyArgumentList
        pixbuf = Gtk.IconTheme.get_default().load_icon('window-close', Gtk.IconSize.SMALL_TOOLBAR,
                                                       Gtk.IconLookupFlags.FORCE_SYMBOLIC)
        image = Gtk.Image(visible=True)
        image.set_from_pixbuf(pixbuf)
        self.set_image(image)
