# import cairo
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GObject

from typing import Any, Optional, Tuple, Dict

from PIL import Image
from xml.sax.saxutils import escape
from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from .base import (
    View,
    FileGroupSelector,
    FileGroupFilter,
    ImageZoomSelector,
    Configurator
)
from ..model import LazyPage
from ..model.page_xml_renderer import PageXmlRenderer, RegionMap, Feature


class PageFeaturesSelector(Gtk.Box, Configurator):

    def __init__(self) -> None:
        super().__init__(visible=True, spacing=3)
        self.value = None
        self.items: Dict[Feature, Gtk.CheckMenuItem] = {}

        menu = Gtk.Menu(visible=True)
        for feature in list(Feature):
            item = Gtk.CheckMenuItem(label=feature.icon + ' ' + feature.label, name=feature.name.upper(), tooltip_text='Show ' + feature.label, visible=True)
            item.connect("toggled", self.on_feature_toggled)
            menu.append(item)
            self.items[feature] = item

        menubutton = Gtk.MenuButton(visible=True)
        menubutton.set_direction(Gtk.ArrowType.UP)
        menubutton.set_popup(menu)

        self.pack_start(menubutton, False, False, 0)

    def on_feature_toggled(self, item: Gtk.CheckMenuItem) -> None:
        toggle_feature: Feature = Feature[item.get_name()]
        if item.get_active():
            self.value = Feature(self.value) | toggle_feature  # type: ignore[call-arg]
        else:
            self.value = Feature(self.value) & ~toggle_feature  # type: ignore[call-arg]
        self.emit('changed', self.value)

    def set_value(self, value: int) -> None:
        self.value = Feature(value)  # type: ignore[call-arg]
        for feature in list(Feature):
            self.items[feature].set_active(feature & value)  # type: ignore[operator]
        self.emit('changed', self.value)

    @GObject.Signal(arg_types=[object])
    def changed(self, features: Feature) -> None:
        self.value = features


class ViewPage(View):
    """
    PageViewer like View
    """

    label = 'Page'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.current: LazyPage = None

        self.file_group: Tuple[Optional[str], Optional[str]] = (None, None)
        self.scale: float = -2.0
        self.features = Feature.default()

        self.preview_height: int = 10
        self.last_rescale = -100
        self.viewport: Optional[Gtk.Viewport] = None
        self.image: Optional[Gtk.Image] = None
        self.page_image: Optional[Image.Image] = None
        self.region_map: Optional[RegionMap] = None

    def build(self) -> None:
        super(ViewPage, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -4.0, 2.0))
        self.add_configurator('features', PageFeaturesSelector())

        self.image = Gtk.Image(visible=True, icon_name='gtk-missing-image', icon_size=Gtk.IconSize.DIALOG)

        # Gtk.EventBox allows to listen for events per view (Gtk.Image doesn't listen, Gtk.Window listen too broad)
        eventbox = Gtk.EventBox(visible=True)
        eventbox.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        eventbox.connect('scroll-event', self.on_scroll)
        eventbox.add(self.image)

        # Momentane Reihenfolge: scroller->viewport->eventbox->image
        # Kaputte  Reihenfolge:  scroller->viewport->eventbox->overlay->image|b

        # overlay = Gtk.Overlay(visible=True)
        # b: Gtk.DrawingArea = Gtk.DrawingArea(visible=True, valign = Gtk.Align.CENTER, halign = Gtk.Align.CENTER)
        # b.set_size_request(200,200)
        # b.connect('draw', self.draw)
        # overlay.add(self.image)
        # overlay.add_overlay(b)
        # eventbox.add(overlay)

        self.image.set_has_tooltip(True)
        self.image.connect('query-tooltip', self._query_tooltip)

        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        self.viewport.connect('size-allocate', self.on_viewport_size_allocate)
        self.viewport.add(eventbox)

        self.scroller.add(self.viewport)

#    def draw(self, area: Gtk.DrawingArea, context: cairo.Context) -> None:
#        context.scale(area.get_allocated_width(), area.get_allocated_height())
#        context.set_source_rgb(0.5, 0.5, 0.7)
#        context.fill()
#        context.paint()

    def config_changed(self, name: str, value: Any) -> None:
        super(ViewPage, self).config_changed(name, value)
        if name == 'features':
            GLib.idle_add(self.redraw, priority=GLib.PRIORITY_DEFAULT_IDLE)
        if name == 'scale':
            GLib.idle_add(self.rescale, priority=GLib.PRIORITY_DEFAULT_IDLE)
        if name == 'file_group':
            GLib.idle_add(self.reload, priority=GLib.PRIORITY_DEFAULT_IDLE)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def redraw(self) -> None:
        if self.current:
            page_image, page_coords, _ = self.current.get_image(feature_selector='', feature_filter='deskewed,binarized,cropped')
            renderer = PageXmlRenderer(page_image, page_coords, self.current.id, self.features)
            renderer.render_all(self.current.pc_gts)
            self.page_image, self.region_map = renderer.get_result()
        else:
            self.page_image, self.region_map = None, None
        GLib.idle_add(self.rescale, True, priority=GLib.PRIORITY_DEFAULT_IDLE)

    def rescale(self, force: bool = False) -> None:
        if self.page_image:
            scale_config: ImageZoomSelector = self.configurators['scale']
            if force or abs(scale_config.value - self.last_rescale) > (scale_config.scale.get_adjustment().get_step_increment() - 0.0001):
                self.last_rescale = scale_config.value
                thumbnail = pil_scale(self.page_image, None, int(scale_config.get_exp() * self.page_image.height))
                self.image.set_from_pixbuf(pil_to_pixbuf(thumbnail))
        else:
            self.image.set_from_stock('missing-image', Gtk.IconSize.DIALOG)

    def on_scroll(self, _widget: Gtk.EventBox, event: Gdk.EventScroll) -> bool:
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

    def on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle) -> None:
        """
        Nothing for now, needed when  we have "fit to width/height"
        """
        pass

    def _query_tooltip(self, _image: Gtk.Image, x: int, y: int, _keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        tx, ty = self.screen_to_image(x, y)
        if tx is None:
            return False

        region = self.region_map.find_region(tx, ty)

        content = '<tt>{:d}, {:d}</tt>'.format(int(tx), int(ty))
        if region:
            content += '\n<tt><big>{}</big></tt>\n\n{}'.format(str(region), escape(region.text))

            if region.warnings:
                content += '\n' + ('\n'.join(region.warnings))

        tooltip.set_markup(content)

        return True

    def screen_to_image(self, x: int, y: int) -> Tuple[Optional[float], Optional[float]]:
        """
        Transforms screen coordinates to image coordinates for centered and scaled `Gtk.Image`s
        """
        if self.image is None:
            return None, None

        pb: GdkPixbuf.Pixbuf = self.image.get_pixbuf()
        if pb is None:
            return None, None

        ww, wh = self.image.get_allocated_width(), self.image.get_allocated_height()
        iw, ih = pb.get_width(), pb.get_height()

        rel_x = (x - (ww - iw) / 2) / iw
        rel_y = (y - (wh - ih) / 2) / ih
        if rel_x < 0 or rel_x > 1 or rel_y < 0 or rel_y > 1:
            return None, None

        return rel_x * self.page_image.width, rel_y * self.page_image.height
