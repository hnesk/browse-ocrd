from gi.repository import Gtk, Gdk, GLib

from typing import Any, Optional, Tuple

from PIL import Image

from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from .base import (
    View,
    FileGroupSelector,
    FileGroupFilter,
    ImageZoomSelector
)
from ..model import LazyPage
from ..model.page_xml_renderer import PageXmlRenderer


class ViewPage(View):
    """
    PageViewer like View
    """

    label = 'Page'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.current: LazyPage = None
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, None)
        self.preview_height: int = 10
        self.scale: float = -2.0
        self.last_rescale = -100
        self.viewport: Optional[Gtk.Viewport] = None
        self.image: Optional[Gtk.Image] = None
        self.page_image: Optional[Image] = None

    def build(self) -> None:
        super(ViewPage, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -4.0, 2.0))

        self.image = Gtk.Image(visible=True, icon_name='gtk-missing-image', icon_size=Gtk.IconSize.DIALOG)

        eventbox = Gtk.EventBox(visible=True)
        eventbox.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        eventbox.connect('scroll-event', self.on_scroll)
        eventbox.add(self.image)

        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        self.viewport.connect('size-allocate', self.on_viewport_size_allocate)
        self.viewport.add(eventbox)

        self.scroller.add(self.viewport)

    def config_changed(self, name: str, value: Any) -> None:
        super(ViewPage, self).config_changed(name, value)
        if name == 'scale':
            GLib.idle_add(self.rescale, priority=GLib.PRIORITY_DEFAULT_IDLE)
        if name == 'file_group':
            GLib.idle_add(self.reload, priority=GLib.PRIORITY_DEFAULT_IDLE)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def redraw(self) -> None:
        if self.current:
            page_image, page_coords, page_image_info = self.current.get_image(feature_selector='binarized', feature_filter='deskewed')
            renderer = PageXmlRenderer(page_image, page_coords, self.current.id)
            renderer.render_all(self.current.pc_gts)
            self.page_image = renderer.get_canvas()
        else:
            self.page_image = None
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
        # Handles zoom in / zoom out on Ctrl+mouse wheel
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
