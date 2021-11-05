from math import log

from gi.repository import Gtk, Pango, GObject

from typing import List, Tuple, Any, Optional, Dict, cast

from enum import Enum

from ocrd_utils.constants import MIMETYPE_PAGE, MIME_TO_EXT
from ocrd_browser.model import Document, Page
from ocrd_browser.util.gtk import WhenIdle


class Configurator(Gtk.Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.document: Optional[Document] = None
        self.value: Any = None

    def set_document(self, document: Document) -> None:
        self.document = document

    def set_page(self, page: Page) -> None:
        pass

    def set_value(self, value: Any) -> None:
        raise NotImplementedError('You have to override set_value')


class View:
    # TODO: Views should announce which mimetype they can handle and be only available if it there is matching mimetype in Document, also they should announce if they can handle a certain Page
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
        self.container = Gtk.Box(visible=True, orientation="vertical", name=self.name)
        self.action_bar = Gtk.ActionBar(visible=True)
        self.action_bar.pack_end(CloseButton(self.name))
        self.action_bar.pack_end(SplitViewButton(self.name, True))
        self.action_bar.pack_end(SplitViewButton(self.name, False))

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
        if page_id != self.page_id:
            self.page_id = page_id
            self.reload()

    def pages_selected(self, _sender: Gtk.Widget, page_ids: List[str]) -> None:
        pass

    def reload(self) -> None:
        if self.page_id:
            self.current = self.document.page_for_id(self.page_id, self.use_file_group)
            if self.current:
                for configurator in self.configurators.values():
                    configurator.set_page(self.current)

        WhenIdle.call(self.redraw)

    def redraw(self) -> None:
        pass

    def update_ui(self) -> None:
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

    def __init__(self, base: float = 2, step: float = 0.1, min_: float = -4.0, max_: float = 2.0) -> None:
        super().__init__(visible=True, spacing=2)
        self.value = None

        self.base = base
        self.scale = Gtk.SpinButton(visible=True, max_length=5, width_chars=5, max_width_chars=5, numeric=True,
                                    digits=2)
        self.scale.set_tooltip_text('Zoom: log{:+.0f} scale factor for viewing images'.format(base))
        # noinspection PyCallByClass,PyArgumentList
        self.scale.set_adjustment(Gtk.Adjustment.new(0.0, min_, max_, step, 0, 0))
        self.scale.set_snap_to_ticks(False)
        self.scale.connect('value-changed', self.value_changed)

        # label = Gtk.Label(label='Zoom:', visible=True)
        # self.pack_start(label, False, True, 0)
        self.pack_start(self.scale, False, True, 0)

    def get_exp(self) -> float:
        return cast(float, self.base ** self.value)

    def set_value(self, value: float) -> None:
        adj: Gtk.Adjustment = self.scale.get_adjustment()
        value = min(adj.get_upper(), max(adj.get_lower(), value))
        self.scale.set_value(value)

    def value_changed(self, spin: Gtk.SpinButton) -> None:
        self.emit('changed', spin.get_value())

    @GObject.Signal(arg_types=[float])
    def changed(self, scale: float) -> None:
        self.value = scale
        self.scale.set_tooltip_text(
            '{:.2%} / log{:.2f} scale factor for viewing images'.format(self.get_exp(), self.base))

    def zoom_by(self, steps: int) -> None:
        """
        Zooms in(`steps` > 0) or out(`steps` < 0) by `steps` steps
        """
        direction = Gtk.SpinType.STEP_FORWARD if steps > 0 else Gtk.SpinType.STEP_BACKWARD
        self.scale.spin(direction, abs(steps) * self.scale.get_adjustment().get_step_increment())

    def zoom_to(self, to: str, width_ratio: float, height_ratio: float) -> None:
        """
        Set zoom to one of
            'original': Original Size
            'width': Fit to width
            'height': Fit to height
            'page': Fit to show whole page
            'viewport': Fit to use whole viewport
        """
        lookup = {
            'original': lambda: 1,
            'width': lambda: width_ratio,
            'height': lambda: height_ratio,
            'page': lambda: min(width_ratio, height_ratio),
            'viewport': lambda: max(width_ratio, height_ratio)
        }
        if to in lookup:
            ratio = lookup[to]()
            self.set_value(log(ratio, self.base))
        else:
            raise ValueError('to was "{}", but needs to be one of {}'.format(to, ', '.join(lookup.keys())))


class FileGroupSelector(Gtk.Box, Configurator):

    def __init__(self, filter_: Optional['FileGroupFilter'] = None, show_mime: bool = False, show_ext: bool = True):
        super().__init__(visible=True, spacing=2)
        self.value = None

        self.groups = FileGroupComboBox(filter_, show_mime, show_ext)

        # label = Gtk.Label(label='Group:', visible=True)
        # self.pack_start(label, False, True, 0)
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
        Gtk.ComboBox.__init__(self, visible=True, has_tooltip=True, popup_fixed_width=False)
        self.set_model(Gtk.ListStore(str, str, str, str))
        self.filter = filter_
        self.set_id_column(self.COLUMN_ID)

        self.add_renderer(self.COLUMN_GROUP)
        if show_mime:
            self.add_renderer(self.COLUMN_MIME, 80)
        if show_ext:
            self.add_renderer(self.COLUMN_EXT)

        self.connect('query-tooltip', self.set_tooltip)

    def set_tooltip(self, _widget: Gtk.Widget, _x: int, _y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        model = self.get_model()
        if len(model) > 0:
            row = self.get_model()[self.get_active()][:]
            phs = {'fileGrp': row[self.COLUMN_GROUP], 'ext': row[self.COLUMN_EXT], 'mime': row[self.COLUMN_MIME]}
            tooltip.set_text('fileGrp: {fileGrp} (Mime-Type: {mime})'.format(**phs))
            return True
        return False

    def set_document(self, document: Document) -> None:
        self.set_model(FileGroupModel.build(document, self.filter))
        # self.set_active(0)

    def add_renderer(self, column: int, width: int = None) -> Gtk.CellRendererText:
        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.MIDDLE)
        if width:
            renderer.props.width = width
        self.pack_start(renderer, False)
        self.add_attribute(renderer, "text", column)
        return renderer


class FileGroupModel(Gtk.ListStore):
    def __init__(self, document: Document):
        super().__init__(str, str, str, str)
        for group, mime in document.file_groups_and_mimetypes:
            if mime == 'text/html':
                ext = '.html'
            else:
                ext = MIME_TO_EXT.get(mime, '.???')
            self.append(('{}|{}'.format(group, mime), group, mime, ext))

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
        return str(model[it][FileGroupComboBox.COLUMN_MIME]) == str(MIMETYPE_PAGE)

    @staticmethod
    def xml_filter(model: Gtk.TreeModel, it: Gtk.TreeIter, _data: None) -> bool:
        return str(model[it][FileGroupComboBox.COLUMN_EXT]) == '.xml'

    @staticmethod
    def html_filter(model: Gtk.TreeModel, it: Gtk.TreeIter, _data: None) -> bool:
        # str casts for mypy
        return str(model[it][FileGroupComboBox.COLUMN_MIME]) == 'text/html'

    @staticmethod
    def all_filter(_model: Gtk.TreeModel, _it: Gtk.TreeIter, _data: None) -> bool:
        return True


class FileGroupFilter(Enum):
    IMAGE = FileGroupModel.image_filter
    PAGE = FileGroupModel.page_filter
    HTML = FileGroupModel.html_filter
    XML = FileGroupModel.xml_filter
    ALL = FileGroupModel.all_filter


class CloseButton(Gtk.Button):
    def __init__(self, view_name: str):
        Gtk.Button.__init__(self, visible=True)
        self.set_name('close_{}'.format(view_name))
        self.set_detailed_action_name('win.close_view("{}")'.format(view_name))
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_always_show_image(True)
        # noinspection PyArgumentList
        self.set_image(Gtk.Image.new_from_icon_name('window-close-symbolic', Gtk.IconSize.SMALL_TOOLBAR))


class SplitViewButton(Gtk.Button):
    def __init__(self, view_name: str, vertical: bool = True):
        Gtk.Button.__init__(self, visible=True)
        direction = 'vertical' if vertical else 'horizontal'
        self.set_name('split_{}_{}'.format(view_name, direction))
        self.set_detailed_action_name('win.split_view(("{}","empty", {}))'.format(view_name, 'true' if vertical else 'false'))
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_always_show_image(True)
        # noinspection PyArgumentList
        self.set_image(Gtk.Image.new_from_icon_name('split-{}'.format(direction), Gtk.IconSize.SMALL_TOOLBAR))
