from gi.repository import Gtk, Gdk, GObject, Pango

from typing import Any, Optional, Tuple, Dict, List, NamedTuple, FrozenSet

from pathlib import Path
from PIL import Image
from cairo import Context
from xml.sax.saxutils import escape

from ocrd_models.ocrd_page_generateds import AlternativeImageType

from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from ocrd_utils.constants import MIMETYPE_PAGE
from .base import (
    View,
    FileGroupSelector,
    FileGroupFilter,
    ImageZoomSelector,
    Configurator
)
from ..model import LazyPage, Page, Document
from ..model.page_xml_renderer import PageXmlRenderer, RegionMap, Feature, Region
from ..util.gtk import WhenIdle


class FeatureDescription:
    def __init__(self, icon: str, label: str, xpath: str, tooltip: str = None):
        self.icon = icon
        self.label = label
        self.xpath = xpath
        self.tooltip = tooltip if tooltip else 'Show ' + label

    def available(self, page: Page) -> bool:
        return len(page.xpath(self.xpath)) > 0


class Transformation:
    """
    Encapsulates forward and inverse affine transform consisting of scaling and translation only
    """
    # TODO: clip to image with page_image sizes
    def __init__(self, scale: float, tx: float, ty: float):
        self.scale = scale
        self.tx = tx
        self.ty = ty

    @classmethod
    def from_image(cls, page_image: Image.Image = Image, widget: Gtk.Image = None) -> Optional['Transformation']:
        # TODO: move to PageXmlRenderer and pass page_image sizes for clipping
        if page_image is None or widget is None or widget.get_pixbuf() is None:
            return None

        pb = widget.get_pixbuf()
        size, _ = widget.get_allocated_size()

        return Transformation(
            page_image.width / pb.get_width(),
            -(size.width - pb.get_width()) / 2,
            -(size.height - pb.get_height()) / 2
        )

    def tranform_region(self, region: Region) -> Tuple[float, float, float, float]:
        (l, t), (r, b) = self.inverse(*region.poly.bounds[0:2]), self.inverse(*region.poly.bounds[2:4])
        return l, t, r - l, b - t

    def transform(self, x: float, y: float) -> Tuple[float, float]:
        return (x + self.tx) * self.scale, (y + self.ty) * self.scale

    def inverse(self, x: float, y: float) -> Tuple[float, float]:
        return x / self.scale - self.tx, y / self.scale - self.ty


class ImageVersion(NamedTuple):
    path: Path
    size: Tuple[int, int]
    features: FrozenSet[str] = frozenset()
    conf: Optional[float] = None

    def as_row(self) -> Tuple[str, str, str]:
        return ','.join(sorted(self.features)), self.path.stem, '{0:d}x{1:d}'.format(*self.size)

    @classmethod
    def from_page(cls, doc: Document, page: Page) -> 'ImageVersion':
        return cls(doc.path(page.page.imageFilename), (page.page.imageWidth, page.page.imageHeight), frozenset(), None)

    @classmethod
    def from_alternative_image(cls, doc: Document, alt: AlternativeImageType) -> 'ImageVersion':
        path = doc.path(alt.filename)
        return cls(
            path,
            Image.open(path).size,
            frozenset(str(alt.comments).split(',')),
            float(alt.conf) if alt.conf is not None else None
        )


class ImageVersionSelector(Gtk.Box, Configurator):

    def __init__(self) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None
        label = Gtk.Label(label='Image:', visible=True)
        label = Gtk.Label(label='Image:', visible=True)

        self.versions = Gtk.ListStore(str, str, str)
        self.version_box = Gtk.ComboBox(visible=True, model=self.versions)
        self.version_box.set_id_column(0)

        self.pack_start(label, False, True, 0)
        self.pack_start(self.version_box, False, True, 0)

        renderer = Gtk.CellRendererText()
        renderer.props.ellipsize = Pango.EllipsizeMode.START
        self.version_box.pack_start(renderer, False)
        self.version_box.add_attribute(renderer, "text", 1)

        renderer = Gtk.CellRendererText()
        self.version_box.pack_start(renderer, False)
        self.version_box.add_attribute(renderer, "text", 2)

        self._change_handler = self.version_box.connect('changed', self.combo_box_changed)

    def set_value(self, value: str) -> None:
        self.value = value
        self.version_box.set_active_id(value)

    @GObject.Signal(arg_types=[str])
    def changed(self, image: str) -> None:
        self.value = image

    def set_page(self, page: Page) -> None:
        versions = []
        if page:
            versions.append(ImageVersion.from_page(self.document, page))
            alts: List[AlternativeImageType] = page.page.get_AlternativeImage()
            for alt in alts:
                versions.append(ImageVersion.from_alternative_image(self.document, alt))

        with self.version_box.handler_block(self._change_handler):
            self.versions.clear()
            for version in versions:
                self.versions.append(version.as_row())
            if self.value is None:
                self.version_box.set_active(0)
            else:
                if self.value != self.version_box.get_active_id():
                    self.version_box.set_active_id(self.value)

    def combo_box_changed(self, combo: Gtk.ComboBox) -> None:
        self.emit('changed', self.version_box.get_active_id())


class PageFeaturesSelector(Gtk.Box, Configurator):

    FEATURES: Dict[Feature, FeatureDescription] = {
        Feature.IMAGE: FeatureDescription('🖺', 'image', '/page:PcGts/page:Page/@imageFilename'),
        Feature.BORDER: FeatureDescription('🗋', 'border', '/page:PcGts/page:Page/page:Border/page:Coords'),
        Feature.PRINT_SPACE: FeatureDescription('🗌', 'printspace', '/page:PcGts/page:Page/page:PrintSpace/page:Coords'),
        Feature.ORDER: FeatureDescription('↯', 'order', '/page:PcGts/page:Page/page:ReadingOrder/*'),
        Feature.REGIONS: FeatureDescription('⬓', 'regions', '/page:PcGts/page:Page/*[not(local-name(.) = "Border" or local-name(.) = "PrintSpace")]/page:Coords'),
        Feature.LINES: FeatureDescription('𝌆', 'lines', '/page:PcGts/page:Page/*//page:TextLine/page:Coords'),
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
        self.current: LazyPage = None

        # Configurators
        self.file_group: Tuple[Optional[str], Optional[str]] = ('OCR-D-OCR-TESS-deu', MIMETYPE_PAGE)
        self.scale: float = -2.0
        self.features: Feature = Feature.DEFAULT
        self.image_version: str = ''

        # GTK
        self.image: Optional[Gtk.Image] = None
        self.highlight: Optional[Gtk.DrawingArea] = None
        self.status_bar: Optional[Gtk.Box] = None

        # Data
        self.page_image: Optional[Image.Image] = None
        self.region_map: Optional[RegionMap] = None
        self.t: Optional[Transformation] = None
        self.current_region: Region = None
        self.last_rescale: int = -100

    def build(self) -> None:
        super(ViewPage, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))
        self.add_configurator('image_version', ImageVersionSelector())
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -4.0, 2.0))
        self.add_configurator('features', PageFeaturesSelector())

        self.image = Gtk.Image(visible=True, icon_name='gtk-missing-image', icon_size=Gtk.IconSize.DIALOG)

        self.highlight = Gtk.DrawingArea(visible=True, valign=Gtk.Align.FILL, halign=Gtk.Align.FILL)
        self.highlight.connect('draw', self.draw_highlight)

        overlay = Gtk.Overlay(visible=True, can_focus=True, has_focus=True, is_focus=True)
        overlay.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        overlay.set_has_tooltip(True)
        overlay.connect('query-tooltip', self._query_tooltip)
        overlay.connect('scroll-event', self._on_scroll)
        overlay.connect('button-press-event', self._on_button)
        overlay.connect('motion-notify-event', self._on_mouse)
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
        print(name, value)
        if name == 'features' or name == 'image_version':
            WhenIdle.call(self.redraw, priority=50)
        if name == 'scale':
            WhenIdle.call(self.rescale)
        if name == 'file_group':
            WhenIdle.call(self.reload, priority=10)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def redraw(self) -> None:
        if self.current:
            # TODO: store self.image_version as a frozenset
            all_classes = frozenset({'binarized', 'grayscale_normalized', 'deskewed', 'despeckled', 'cropped', 'rotated-90', 'rotated-180', 'rotated-270'})
            selected = frozenset(self.image_version.split(','))
            page_image, page_coords, _ = self.current.get_image(feature_selector=','.join(selected), feature_filter=','.join(all_classes.difference(selected)))
            renderer = PageXmlRenderer(page_image, page_coords, self.current.id, self.features)
            renderer.render_all(self.current.pc_gts)
            self.page_image, self.region_map = renderer.get_result()
        else:
            self.page_image, self.region_map = None, None
        WhenIdle.call(self.rescale, force=True)

    def rescale(self, force: bool = False) -> None:
        if self.page_image:
            scale_config: ImageZoomSelector = self.configurators['scale']
            if force or abs(scale_config.value - self.last_rescale) > (scale_config.scale.get_adjustment().get_step_increment() - 0.0001):
                self.last_rescale = scale_config.value
                thumbnail = pil_scale(self.page_image, None, int(scale_config.get_exp() * self.page_image.height))
                self.image.set_from_pixbuf(pil_to_pixbuf(thumbnail))
        else:
            self.image.set_from_stock('missing-image', Gtk.IconSize.DIALOG)
        self.t = Transformation.from_image(self.page_image, self.image)
        self.highlight.queue_draw()

    def _on_mouse(self, _widget: Gtk.Overlay, e: Gdk.EventButton) -> None:
        if not (self.t is None or self.region_map is None):
            tx, ty = self.t.transform(e.x, e.y)
            if self.region_map.find_region(tx, ty, ignore_regions=[]):
                watch = Gdk.Cursor.new_from_name(self.container.get_display(), 'pointer')
                self.container.get_window().set_cursor(watch)
                return

        watch = Gdk.Cursor.new_from_name(self.container.get_display(), 'default')
        self.container.get_window().set_cursor(watch)

    def _on_button(self, _widget: Gtk.Overlay, e: Gdk.EventButton) -> bool:
        _widget.grab_focus()
        old_region = self.current_region
        if self.t is None or self.region_map is None:
            self.current_region = None
        else:
            tx, ty = self.t.transform(e.x, e.y)
            self.current_region = self.region_map.find_region(tx, ty, ignore_regions=[])

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
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            did_scroll, delta_x, delta_y = event.get_scroll_deltas()
            if did_scroll and abs(delta_y) > 0:
                scale_config: ImageZoomSelector = self.configurators['scale']
                scale_config.set_value(self.scale + delta_y * 0.1)
                return True
        return False

    def _on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle) -> None:
        """
        Nothing for now, needed when  we have "fit to width/height"
        """
        self.t = Transformation.from_image(self.page_image, self.image)
        self.highlight.queue_draw()

    def _query_tooltip(self, _image: Gtk.Image, x: int, y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        if self.t is None:
            return False

        tx, ty = self.t.transform(x, y)

        region = self.region_map.find_region(tx, ty, ignore_regions=[])

        content = '<tt>{:d}, {:d}</tt>'.format(int(tx), int(ty))
        if region:
            content += '\n<tt><big>{}</big></tt>\n\n{}'.format(str(region), escape(region.text))

            if region.warnings:
                content += '\n' + ('\n'.join(region.warnings))

        tooltip.set_markup(content)

        return True

    def update_status_bar(self) -> None:
        for w in self.status_bar.get_children():
            self.status_bar.remove(w)

        if self.current_region:
            for i, r in enumerate(reversed(self.current_region.breadcrumbs())):
                if i:
                    self.status_bar.pack_start(Gtk.Separator(visible=True, orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

                label = Gtk.Label(visible=True, label=str(r), ellipsize=Pango.EllipsizeMode.MIDDLE, max_width_chars=20, tooltip_text=str(r))
                self.status_bar.pack_start(label, False, False, 5)
        else:
            self.status_bar.pack_start(Gtk.Label(visible=True, label='---'), False, False, 2)

    def invalidate_region(self, r: Region) -> None:
        if r:
            x, y, w, h = self.t.tranform_region(r)
            if w > 0 and h > 0:
                self.highlight.queue_draw_area(x, y, w, h)

    def draw_highlight(self, _area: Gtk.DrawingArea, context: Context) -> None:
        if self.current_region and self.t:
            context.set_source_rgba(0.75, 1, 0.5, 0.33)
            context.new_path()
            for px, py in self.current_region.poly.exterior.coords:
                context.line_to(*self.t.inverse(px, py))
            context.close_path()
            context.fill()
