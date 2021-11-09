from gi.repository import Gtk, Gdk, GLib, Gio

from typing import Any, List, Optional, Tuple

from itertools import zip_longest
from ocrd_browser.util.image import pil_to_pixbuf, pil_scale
from ocrd_models.constants import NAMESPACES as NS
from .base import (
    View,
    FileGroupSelector,
    FileGroupFilter,
    PageQtySelector,
    ImageZoomSelector
)
from ..model import Page
from ..util.gtk import WhenIdle, ActionRegistry


class ViewImages(View):
    """
    View of one or more consecutive images
    """

    label = 'Image'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, None)
        self.page_qty: int = 1
        self.preview_height: int = 10
        self.scale: float = -2.0
        self.last_rescale = -100
        self.viewport: Optional[Gtk.Viewport] = None
        self.image_box: Optional[Gtk.Box] = None
        self.pages: List[Page] = []

    def build(self) -> None:
        super(ViewImages, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.IMAGE))
        self.add_configurator('page_qty', PageQtySelector())
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -4.0, 2.0))

        self.image_box = Gtk.Box(visible=True, orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)

        eventbox = Gtk.EventBox(visible=True, can_focus=True, has_focus=True, focus_on_click=True, is_focus=True)
        eventbox.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        eventbox.connect('scroll-event', self.on_scroll)
        eventbox.connect('button-press-event', self.on_button)
        eventbox.add(self.image_box)

        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        self.viewport.connect('size-allocate', self._on_viewport_size_allocate)
        self.viewport.add(eventbox)

        self.scroller.add(self.viewport)

        actions = ActionRegistry()
        actions.create(name='zoom_by', param_type=GLib.VariantType('i'), callback=self._on_zoom_by)
        actions.create(name='zoom_to', param_type=GLib.VariantType('s'), callback=self._on_zoom_to)
        eventbox.insert_action_group("view", actions.for_widget)

        self.rebuild_pages()

    def config_changed(self, name: str, value: Any) -> None:
        super(ViewImages, self).config_changed(name, value)
        if name == 'page_qty':
            WhenIdle.call(self.rebuild_pages, priority=1)
        if name == 'file_group':
            WhenIdle.call(self.reload, priority=10)
        if name == 'scale':
            WhenIdle.call(self.rescale)

    def rebuild_pages(self) -> None:
        existing_pages = {child.get_name(): child for child in self.image_box.get_children()}

        # We need a variable number of Gtk.Image (depending on number of AlternativeImage)
        # in a fixed number of Gtk.VBox (depending on configured page_qty)
        # in a single Gtk.HBox (for the current view).
        # So whenever page_qty changes, some HBoxes will be re-used,
        # and whenever page_id changes, some VBoxes will be re-used.
        for i in range(0, self.page_qty):
            name = 'page_{}'.format(i)
            if not existing_pages.pop(name, None):
                page = Gtk.Box(visible=True, orientation=Gtk.Orientation.VERTICAL, homogeneous=False, spacing=0)
                self.image_box.add(page)

        for child in existing_pages.values():
            child.destroy()

        WhenIdle.call(self.reload, priority=10)

    def page_activated(self, _sender: Gtk.Widget, page_id: str) -> None:
        self.page_id = page_id
        WhenIdle.call(self.reload)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def reload(self) -> None:
        if self.document:
            display_ids = self.document.display_id_range(self.page_id, self.page_qty)
            self.pages = []
            for display_id in display_ids:
                self.pages.append(self.document.page_for_id(display_id, self.use_file_group))
        WhenIdle.call(self.redraw)

    def redraw(self) -> None:
        if self.pages:
            box: Gtk.Box
            for box, page in zip_longest(self.image_box.get_children(), self.pages):
                existing_images = {child.get_name(): child for child in box.get_children()}
                for i, img in enumerate(page.images if page else [None]):
                    name = 'image_{}'.format(i)
                    image: Gtk.Image
                    image = existing_images.pop(name, None)
                    if not image:
                        image = Gtk.Image(name=name, visible=True,
                                          icon_name='gtk-missing-image',
                                          icon_size=Gtk.IconSize.DIALOG)
                        box.add(image)
                    if img:
                        if page.image_files[0] == page.file:
                            # PAGE-XML was created from the (first) image file directly
                            image.set_tooltip_text(page.id)
                        else:
                            img_file = page.image_files[i]
                            # get segment ID for AlternativeImage as tooltip
                            img_id = page.pc_gts.gds_elementtree_node_.xpath(
                                '//page:AlternativeImage[@filename="{}"]/../@id'.format(img_file.local_filename),
                                namespaces=NS)
                            if img_id:
                                image.set_tooltip_text(page.id + ':' + img_id[0])
                            else:
                                image.set_tooltip_text(img_file.local_filename)
                    else:
                        image.set_from_icon_name('missing-image', Gtk.IconSize.DIALOG)
                for child in existing_images.values():
                    child.destroy()
            WhenIdle.call(self.rescale, force=True)

    def rescale(self, force: bool = False) -> None:
        if self.pages:
            box: Gtk.Box
            scale_config: ImageZoomSelector = self.configurators['scale']
            if force or abs(scale_config.value - self.last_rescale) > (scale_config.scale.get_adjustment().get_step_increment() - 0.0001):
                self.last_rescale = scale_config.value
                for box, page in zip_longest(self.image_box.get_children(), self.pages):
                    images = {child.get_name(): child for child in box.get_children()}
                    for i, img in enumerate(page.images if page else [None]):
                        name = 'image_{}'.format(i)
                        image: Gtk.Image
                        image = images[name]
                        if img:
                            thumbnail = pil_scale(img, None, int(scale_config.get_exp() * img.height))
                            image.set_from_pixbuf(pil_to_pixbuf(thumbnail))

    def on_button(self, _widget: Gtk.EventBox, event: Gdk.EventButton) -> bool:
        _widget.grab_focus()
        return False

    def on_scroll(self, _widget: Gtk.EventBox, event: Gdk.EventScroll) -> bool:
        _widget.grab_focus()
        # Handles zoom in / zoom out on Ctrl+mouse wheel
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

    def _on_zoom_by(self, _action: Gio.SimpleAction, steps_v: Optional[GLib.Variant] = None) -> None:
        scale_config: ImageZoomSelector = self.configurators['scale']
        scale_config.zoom_by(steps_v.get_int32())

    def _on_zoom_to(self, _action: Gio.SimpleAction, to_v: Optional[GLib.Variant] = None) -> None:
        scale_config: ImageZoomSelector = self.configurators['scale']
        all_width = 0
        all_height = 0
        for page in self.pages:
            page_height = 0
            page_width = 0
            for image in page.images:
                page_height += image.height
                page_width = max(page_width, image.width)
            all_height = max(all_height, page_height)
            all_width += page_width

        scale_config.zoom_to(
            to_v.get_string(),
            self.viewport_size.width / all_width,
            self.viewport_size.height / all_height
        )
