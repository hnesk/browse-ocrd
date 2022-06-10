from gi.repository import Gtk, Gdk, GObject, Pango, Gio, GLib

from typing import Any, Optional, Tuple, Dict, List, NamedTuple, FrozenSet

from pathlib import Path
from PIL import Image
from cairo import Context
from xml.sax.saxutils import escape

from ocrd_models.ocrd_page import AlternativeImageType
from shapely.geometry import Polygon

from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from ocrd_utils.constants import MIMETYPE_PAGE
from .base import (
    View,
    FileGroupSelector,
    FileGroupFilter,
    ImageZoomSelector,
    Configurator
)
from ..model import Page, Document, IMAGE_FROM_PAGE_FILENAME_SUPPORT
from ..model.page_xml_renderer import PageXmlRenderer, RegionMap, Feature, Region
from ..util.gtk import WhenIdle, ActionRegistry


class FeatureDescription:
    def __init__(self, icon: str, label: str, xpath: str, tooltip: str = None):
        self.icon = icon
        self.label = label
        self.xpath = xpath
        self.tooltip = tooltip if tooltip else 'Show ' + label

    def available(self, page: Page) -> bool:
        return len(page.xpath(self.xpath)) > 0


def clamp(x: float, lower: float, upper: float) -> float:
    return lower if x < lower else upper if x > upper else x


class Transformation:
    """
    Encapsulates forward and inverse affine transform consisting of scaling and translation only
    """
    def __init__(self, scale: float, tx: float, ty: float, cx: float, cy: float):
        self.scale = scale
        self.tx = tx
        self.ty = ty
        self.cx = cx
        self.cy = cy

    def transform_region(self, poly: Polygon) -> Tuple[float, float, float, float]:
        (l, t), (r, b) = self.inverse(*poly.bounds[0:2]), self.inverse(*poly.bounds[2:4])
        return l, t, r - l, b - t

    def transform(self, x: float, y: float) -> Tuple[float, float]:
        return clamp((x + self.tx) * self.scale, 0, self.cx), clamp((y + self.ty) * self.scale, 0, self.cy)

    def inverse(self, x: float, y: float) -> Tuple[float, float]:
        return clamp(x, 0, self.cx) / self.scale - self.tx, clamp(y, 0, self.cy) / self.scale - self.ty


class ImageFeatures:
    FEATURES = {
        'binarized': 'B',
        'grayscale_normalized': 'N',
        'deskewed': 'S',
        'despeckled': 'P',
        'dewarped': 'W',
        'cropped': 'C',
        'rotated-90': '',
        'rotated-180': '',
        'rotated-270': '',
    }

    @classmethod
    def allowed(cls) -> FrozenSet[str]:
        return frozenset(cls.FEATURES.keys())

    @classmethod
    def from_string(cls, string: str) -> FrozenSet[str]:
        return frozenset(str(string).split(',')).intersection(cls.allowed())

    @classmethod
    def negate(cls, st: FrozenSet[str]) -> FrozenSet[str]:
        return cls.allowed().difference(st.intersection(cls.allowed()))

    @classmethod
    def short(cls, st: FrozenSet[str]) -> str:
        return ''.join([cls.FEATURES[i] for i in st if i in cls.FEATURES])


class ImageVersion(NamedTuple):
    path: Path
    size: Tuple[int, int]
    features: FrozenSet[str] = frozenset()
    conf: Optional[float] = None

    def as_row(self) -> Tuple[str, str, str, str, str]:
        return ','.join(sorted(self.features)), '{0:d}✕{1:d}'.format(*self.size), ImageFeatures.short(self.features), str(self.path), self.path.parent.name

    @classmethod
    def list_from_page(cls, doc: Document, page: Page) -> List['ImageVersion']:
        versions = []
        if page:
            path = doc.path(page.page.imageFilename)
            if path.exists():
                versions.append(cls(path.relative_to(doc.directory), (page.page.imageWidth, page.page.imageHeight), frozenset(), None))
            alts: List[AlternativeImageType] = page.page.get_AlternativeImage()
            for alt in alts:
                path = doc.path(alt.filename)
                if path.exists():
                    versions.append(cls(path.relative_to(doc.directory), Image.open(path).size, frozenset(str(alt.comments).split(',')), float(alt.conf) if alt.conf is not None else None))
        return versions


class ImageVersionSelector(Gtk.Box, Configurator):

    COLUMN_FEATURES = 0
    COLUMN_SIZE = 1
    COLUMN_SHORT_FEATURES = 2
    COLUMN_PATH = 3
    COLUMN_FILE_GROUP = 4

    def __init__(self) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None

        self.versions = Gtk.ListStore(str, str, str, str, str)
        self.version_box = Gtk.ComboBox(visible=True, model=self.versions)

        self.version_box.set_id_column(self.COLUMN_PATH)

        # label = Gtk.Label(label='Image:', visible=True)
        # self.pack_start(label, False, True, 0)
        self.pack_start(self.version_box, False, True, 0)

        renderer = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.START)
        self.version_box.pack_start(renderer, False)
        self.version_box.add_attribute(renderer, "text", self.COLUMN_FILE_GROUP)
        self.set_tooltip_text('Image-Version')

        renderer = Gtk.CellRendererText()
        self.version_box.pack_start(renderer, False)
        self.version_box.add_attribute(renderer, "text", self.COLUMN_SHORT_FEATURES)

        self._change_handler = self.version_box.connect('changed', self.combo_box_changed)

        self.connect('query-tooltip', self.set_tooltip)

    def set_tooltip(self, _widget: Gtk.Widget, _x: int, _y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        model = self.versions
        if len(model) > 0:
            row = model[self.version_box.get_active()][:]
            phs = {
                'features': row[self.COLUMN_FEATURES],
                'size': row[self.COLUMN_SIZE],
                'short_features': row[self.COLUMN_SHORT_FEATURES],
                'path': row[self.COLUMN_PATH],
                'file_group': row[self.COLUMN_FILE_GROUP],
            }
            tooltip.set_text('{path}\t {size}\t{features}'.format(**phs))
            return True
        return False

    def set_value(self, value: Tuple[str, str]) -> None:
        self.value = value
        if value and value[0]:
            self.version_box.set_active_id(value[0])

    @GObject.Signal()
    def changed(self, path: str, features: str) -> None:
        self.value = (path, features)

    def set_page(self, page: Page) -> None:
        previous_selected = None, None
        if self.version_box.get_active() != -1:
            row = self.versions[self.version_box.get_active()]
            previous_selected = row[self.COLUMN_FILE_GROUP], row[self.COLUMN_FEATURES]

        with self.version_box.handler_block(self._change_handler):
            self.versions.clear()
            for version in ImageVersion.list_from_page(self.document, page):
                self.versions.append(version.as_row())

        if self.value is None or self.value[0] is None:
            self.version_box.set_active(0)
        else:
            if self.value[0] != self.version_box.get_active_id():
                for v in self.versions:
                    if v[self.COLUMN_FILE_GROUP] == previous_selected[0] and v[self.COLUMN_FEATURES] == previous_selected[1]:
                        self.version_box.set_active_id(v[self.COLUMN_PATH])
                        return
            self.version_box.set_active_id(self.value[0])

    def combo_box_changed(self, combo: Gtk.ComboBox) -> None:
        if len(self.versions) > 0:
            row = self.versions[combo.get_active()][:]
            self.emit('changed', row[self.COLUMN_PATH], row[self.COLUMN_FEATURES])


class PageFeaturesSelector(Gtk.Box, Configurator):

    FEATURES: Dict[Feature, FeatureDescription] = {
        Feature.IMAGE: FeatureDescription('🖺', 'image', '/page:PcGts/page:Page/@imageFilename'),
        Feature.BORDER: FeatureDescription('🗋', 'border', '/page:PcGts/page:Page/page:Border/page:Coords'),
        Feature.PRINT_SPACE: FeatureDescription('🗌', 'printspace', '/page:PcGts/page:Page/page:PrintSpace/page:Coords'),
        Feature.ORDER: FeatureDescription('↯', 'order', '/page:PcGts/page:Page/page:ReadingOrder/*'),
        Feature.REGIONS: FeatureDescription('⬓', 'regions', '/page:PcGts/page:Page/*[not(local-name(.) = "Border" or local-name(.) = "PrintSpace")]/page:Coords'),
        Feature.LINES: FeatureDescription('𝌆', 'lines', '/page:PcGts/page:Page/*//page:TextLine/page:Coords'),
        Feature.BASELINES: FeatureDescription('–', 'baselines', '/page:PcGts/page:Page/*//page:TextLine/page:Baseline'),
        Feature.WORDS: FeatureDescription('𝌶', 'words', '/page:PcGts/page:Page/*//page:TextLine/page:Word/page:Coords'),
        Feature.GLYPHS: FeatureDescription('𝍖', 'glyphs', '/page:PcGts/page:Page/*//page:TextLine/page:Word/page:Glyph/page:Coords'),
        # Feature.GRAPHEMES: FeatureDescription('#', 'graphemes', '/page:PcGts/page:Page/*//page:TextLine/page:Word/page:Glyph/page:Graphemes/*/page:Coords')
        Feature.WARNINGS: FeatureDescription('‽', 'warnings', '/page:PcGts/page:Page//page:Coords', 'Mark regions with warnings in red')
    }

    def __init__(self) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None
        self.items: Dict[Feature, Gtk.CheckMenuItem] = {}

        menubutton = Gtk.MenuButton(label='Show:', visible=True)
        self.menu_label: Gtk.AccelLabel = menubutton.get_child()

        menu = Gtk.Menu(visible=True)
        for feature, desc in self.FEATURES.items():
            item = Gtk.CheckMenuItem(label=desc.label, name=feature.name, tooltip_text=desc.tooltip, visible=True)
            item.get_child().set_markup('<tt>{0.icon}</tt>\t{0.label}'.format(desc))
            item.connect("toggled", self.on_feature_toggled)
            self.items[feature] = item
            menu.append(item)

        menubutton.set_direction(Gtk.ArrowType.DOWN)
        menubutton.set_popup(menu)

        self.pack_start(menubutton, False, False, 0)

    def on_feature_toggled(self, item: Gtk.CheckMenuItem) -> None:
        toggle_feature: Feature = Feature[item.get_name()]
        if item.get_active():
            self.value = Feature(self.value) | toggle_feature
        else:
            self.value = Feature(self.value) & ~toggle_feature
        self.emit('changed', self.value)

    def update_label_markup(self) -> None:
        markup = 'Show: '
        for feature, desc in self.FEATURES.items():
            s = '<tt>' + desc.icon + '</tt>'
            if not self.items[feature].get_sensitive():
                s = '<span background="#eeeeee" foreground="#bbbbbb">{}</span>'.format(s)
            elif self.items[feature].get_active():
                s = '<span background="#ffffff" foreground="#000000"><b>{}</b></span>'.format(s)
            else:
                s = '<span background="#ffffff" foreground="#999999">{}</span>'.format(s)

            markup += s
        self.menu_label.set_markup(markup)

    def set_value(self, value: int) -> None:
        self.value = Feature(value)
        for feature in self.FEATURES:
            self.items[feature].set_active(feature & value)
        self.emit('changed', self.value)

    @GObject.Signal(arg_types=[object])
    def changed(self, features: Feature) -> None:
        self.update_label_markup()
        self.value = features

    def set_page(self, page: Page) -> None:
        if page:
            for feature, desc in self.FEATURES.items():
                self.items[feature].set_sensitive(desc.available(page))
            self.update_label_markup()


class ViewPage(View):
    """
    PageViewer like View
    """

    label = 'Page'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.current: Optional[Page] = None

        # Configurators
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, MIMETYPE_PAGE)
        self.scale: float = -2.0
        self.image_version: Tuple[Optional[str], str] = (None, '')
        self.features: Feature = Feature.DEFAULT

        # GTK
        self.image: Optional[Gtk.Image] = None
        self.highlight: Optional[Gtk.DrawingArea] = None
        self.status_bar: Optional[Gtk.Box] = None

        # Data
        self.page_image: Optional[Image.Image] = None
        self.region_map: Optional[RegionMap] = None
        self.t: Optional[Transformation] = None
        self.current_region: Optional[Region] = None
        self.last_rescale: int = -100
        self.viewport_size: Gdk.Rectangle

    def build(self) -> None:
        super(ViewPage, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -4.0, 2.0))
        self.add_configurator('image_version', ImageVersionSelector())
        self.add_configurator('features', PageFeaturesSelector())
        icon = Gtk.Image.new_from_icon_name('camera-photo', Gtk.IconSize.SMALL_TOOLBAR)
        button = Gtk.Button(image=icon, visible=True, always_show_image=True, tooltip_text='Saves a screenshot of the current view')
        button.connect('clicked', self.open_screenshotdialog)
        self.action_bar.pack_start(button)

        actions = ActionRegistry()
        actions.create(name='zoom_by', param_type=GLib.VariantType('i'), callback=self._on_zoom_by)
        actions.create(name='zoom_to', param_type=GLib.VariantType('s'), callback=self._on_zoom_to)

        self.image = Gtk.Image(visible=True, icon_name='gtk-missing-image', icon_size=Gtk.IconSize.DIALOG, valign=Gtk.Align.START)

        self.highlight = Gtk.DrawingArea(visible=True, valign=Gtk.Align.FILL, halign=Gtk.Align.FILL, can_focus=True, has_focus=True, focus_on_click=True, is_focus=True)
        self.highlight.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.highlight.set_has_tooltip(True)
        self.highlight.connect('query-tooltip', self._query_tooltip)
        self.highlight.connect('scroll-event', self._on_scroll)
        self.highlight.connect('button-press-event', self._on_button)
        self.highlight.connect('motion-notify-event', self._on_mouse)
        self.highlight.connect('draw', self.draw_highlight)
        self.highlight.insert_action_group("view", actions.for_widget)

        overlay = Gtk.Overlay(visible=True)
        overlay.add(self.image)
        overlay.add_overlay(self.highlight)

        viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        viewport.connect('size-allocate', self._on_viewport_size_allocate)
        viewport.add(overlay)

        self.scroller.add(viewport)
        self.status_bar = Gtk.Box(visible=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.container.pack_end(self.status_bar, False, False, 0)
        self.update_status_bar()

    def config_changed(self, name: str, value: Any) -> None:
        super(ViewPage, self).config_changed(name, value)
        if name == 'file_group':
            WhenIdle.call(self.reload, priority=10)
        if name == 'features' or name == 'image_version':
            WhenIdle.call(self.redraw, priority=50)
        if name == 'scale':
            WhenIdle.call(self.rescale)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def redraw(self) -> None:
        got_result = False
        if self.current:
            selected_features = ImageFeatures.from_string(self.image_version[1])
            parameters = {
                'feature_selector': ','.join(selected_features),
                'feature_filter': ','.join(ImageFeatures.negate(selected_features))
            }
            if IMAGE_FROM_PAGE_FILENAME_SUPPORT:
                parameters['filename'] = self.image_version[0]
            page_image, page_coords, _ = self.current.get_image(**parameters)
            if page_image:
                renderer = PageXmlRenderer(page_image, page_coords, self.current.id, self.features)
                renderer.render_all(self.current.pc_gts)
                self.page_image, self.region_map = renderer.get_result()
                self.current_region = self.region_map.refetch(self.current_region)
                got_result = True
        if not got_result:
            self.page_image, self.region_map = None, None
        self.update_transformation()
        WhenIdle.call(self.rescale, force=True)

    def rescale(self, force: bool = False) -> None:
        if self.page_image:
            scale_config: ImageZoomSelector = self.configurators['scale']
            if force or abs(scale_config.value - self.last_rescale) > (scale_config.scale.get_adjustment().get_step_increment() - 0.0001):
                self.last_rescale = scale_config.value
                thumbnail = pil_scale(self.page_image, None, int(scale_config.get_exp() * self.page_image.height))
                self.image.set_from_pixbuf(pil_to_pixbuf(thumbnail))
        else:
            self.image.set_from_icon_name('missing-image', Gtk.IconSize.DIALOG)
        self.update_transformation()

    def _on_mouse(self, _widget: Gtk.Overlay, e: Gdk.EventButton) -> None:
        if self.t is None or self.region_map is None:
            return

        tx, ty = self.t.transform(e.x, e.y)
        if self.region_map.find_region(tx, ty, ignore_regions=[]):
            # noinspection PyArgumentList
            cursor = Gdk.Cursor.new_from_name(self.container.get_display(), 'pointer')
            self.container.get_window().set_cursor(cursor)
            return

        # noinspection PyArgumentList
        cursor = Gdk.Cursor.new_from_name(self.container.get_display(), 'default')
        self.container.get_window().set_cursor(cursor)

    def _on_button(self, _widget: Gtk.Overlay, e: Gdk.EventButton) -> bool:
        _widget.grab_focus()
        old_region = self.current_region
        if self.t is None or self.region_map is None:
            self.current_region = None
        else:
            tx, ty = self.t.transform(e.x, e.y)
            self.current_region = self.region_map.find_region(tx, ty)

        if self.current_region is not old_region:
            self.invalidate_region(self.current_region)
            self.invalidate_region(old_region)
            self.update_status_bar()

        if e.button == Gdk.BUTTON_SECONDARY and e.type == Gdk.EventType.BUTTON_PRESS:
            if self.current_region:
                self._on_context_menu(e, self.current_region)
        return False

    def _on_context_menu(self, e: Gdk.EventButton, r: Region) -> bool:
        p = Gtk.Menu(visible=True)
        p.append(Gtk.MenuItem(visible=True, label=r.id))
        p.append(Gtk.MenuItem(visible=True, label=r.text))
        p.popup_at_pointer(e)
        return False

    def _on_scroll(self, _widget: Gtk.EventBox, event: Gdk.EventScroll) -> bool:
        """
        Handles zoom in / zoom out on Ctrl+mouse wheel
        """
        _widget.grab_focus()
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            did_scroll, delta_x, delta_y = event.get_scroll_deltas()
            if did_scroll and abs(delta_y) > 0:
                scale_config: ImageZoomSelector = self.configurators['scale']
                scale_config.set_value(self.scale + delta_y * 0.1)
                return True
        return False

    def _on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle) -> None:
        self.viewport_size = rect
        self.update_transformation()

    def _on_zoom_by(self, _action: Gio.SimpleAction, steps_v: Optional[GLib.Variant] = None) -> None:
        scale_config: ImageZoomSelector = self.configurators['scale']
        scale_config.zoom_by(steps_v.get_int32())
        self.update_transformation()

    def _on_zoom_to(self, _action: Gio.SimpleAction, to_v: Optional[GLib.Variant] = None) -> None:
        scale_config: ImageZoomSelector = self.configurators['scale']
        scale_config.zoom_to(
            to_v.get_string(),
            self.viewport_size.width / self.page_image.width,
            self.viewport_size.height / self.page_image.height
        )
        self.update_transformation()

    def _query_tooltip(self, _image: Gtk.Image, x: int, y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        if self.t is None or self.region_map is None:
            return False

        tx, ty = self.t.transform(x, y)

        region = self.region_map.find_region(tx, ty, ignore_regions=[])

        content = '<tt>{:d}, {:d}</tt>'.format(int(tx), int(ty))
        if region:
            content += '\n<tt><big>{}</big></tt>\n\n{}\n'.format(str(region), escape(region.text))

            if region.text_conf:
                content += '\n<tt>@text.conf=</tt>{}'.format(region.text_conf)

            if region.coords_conf:
                content += '\n<tt>@coords.conf=</tt>{}'.format(region.coords_conf)
            if region.region_subtype:
                content += '\n<tt>@type:</tt> {}'.format(region.region_subtype)
            for attribute in [
                    'custom',
                    'comments',
                    'production',
                    'orientation',
                    'leading',
                    'indented',
                    'continuation',
                    'readingDirection',
                    'readingOrientation',
                    'textLineOrder',
                    'primaryLanguage',
                    'secondaryLanguage',
                    'language',
                    'primaryScript',
                    'secondaryScript',
                    'script',
                    'ligature',
                    'symbol',
                    'colourDepth',
                    'bgColour',
                    'embText',
                    'penColour',
                    'numColours',
                    'lineColour',
                    'lineSeparators',
                    'rows',
                    'columns',
                    'colour',
            ]:
                if hasattr(region.region, attribute) and getattr(region.region, attribute):
                    content += '\n<tt>@{}=</tt>{}'.format(attribute, getattr(region.region, attribute))
            if hasattr(region.region, 'TextStyle') and getattr(region.region, 'TextStyle'):
                style = getattr(region.region, 'TextStyle')
                for attribute in [
                        'textColour',
                        'bgColour',
                        'textColourRgb',
                        'bgColourRgb',
                        'reverseVideo',
                        'fontSize',
                        'xHeight',
                        'kerning',
                        'fontFamily',
                        'serif',
                        'monospace',
                        'bold',
                        'italic',
                        'underlined',
                        'underlineStyle',
                        'subscript',
                        'superscript',
                        'strikethrough',
                        'smallCaps',
                        'letterSpaced',
                ]:
                    if getattr(style, attribute):
                        content += '\n<tt>@{}=</tt>{}'.format(attribute, getattr(style, attribute))
            if region.warnings:
                content += '\n\nWarnings:' + ('\n '.join(region.warnings))

        tooltip.set_markup(content)

        return True

    def update_status_bar(self) -> None:
        for w in self.status_bar.get_children():
            self.status_bar.remove(w)

        if self.current_region:
            for i, r in enumerate(reversed(self.current_region.breadcrumbs())):
                if i:
                    self.status_bar.pack_start(Gtk.Separator(visible=True, orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

                label = Gtk.Label(visible=True, label=str(r), ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=20, tooltip_text=str(r))
                self.status_bar.pack_start(label, False, False, 5)
        else:
            self.status_bar.pack_start(Gtk.Label(visible=True, label=' '), False, False, 2)

    def invalidate_region(self, r: Region) -> None:
        if self.t is None or r is None:
            return

        x, y, w, h = self.t.transform_region(r.poly.buffer(5))
        if w > 0 and h > 0:
            self.highlight.queue_draw_area(x, y, w, h)

    def draw_highlight(self, _area: Gtk.DrawingArea, context: Context) -> None:
        if self.current_region and self.t:
            poly: Polygon = self.current_region.poly
            poly = poly.buffer(1, single_sided=True)
            # TODO: 239, 134, 97, 0.7 taken from gtk.css, possible to get it from os????
            context.set_source_rgba(239 / 255.0, 134 / 255.0, 97 / 255.0, 0.7)
            context.set_line_width(clamp(self.configurators['scale'].get_exp() * 12, 0.5, 5))
            context.new_path()
            # Nice idea, but didn't work with scrolling: context.set_matrix(Matrix(1.0/self.t.scale, 0, 0, 1.0/self.t.scale, -self.t.tx, -self.t.ty))
            for coord in poly.exterior.coords:
                context.line_to(*self.t.inverse(*coord))
            context.close_path()
            context.stroke()

    def update_transformation(self) -> None:
        if self.page_image is None or self.image is None or self.image.get_pixbuf() is None:
            return

        pb = self.image.get_pixbuf()
        size, _ = self.image.get_allocated_size()

        self.t = Transformation(
            self.page_image.width / pb.get_width(),
            -(size.width - pb.get_width()) * 0.5,
            -size.height * 0.0 + pb.get_height() * 0.0,
            self.page_image.width,
            self.page_image.height
        )
        self.highlight.queue_draw()

    def open_screenshotdialog(self, button: Gtk.Button) -> None:
        if self.page_image is None:
            return

        dialog = Gtk.FileChooserDialog(title="Save image under...",
                                       parent=self.window,
                                       action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL,
                           Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE,
                           Gtk.ResponseType.OK)
        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG image files")
        filter_png.add_mime_type("image/png")
        dialog.add_filter(filter_png)
        dialog.set_current_name("untitled.png")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else:
            filename = ''

        dialog.destroy()
        if filename:
            self.page_image.save(filename)
