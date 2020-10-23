from gi.repository import Gtk, Gdk

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


class ViewImages(View):
    """
    View of one or more consecutive images
    """

    label = 'Image'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.file_group: Tuple[Optional[str], Optional[str]] = ('OCR-D-IMG', None)
        self.page_qty: int = 1
        self.preview_height: int = 10
        self.scale: float = -1.0
        self.viewport: Optional[Gtk.Viewport] = None
        self.image_box: Optional[Gtk.Box] = None
        self.pages: List[Page] = []

    def build(self) -> None:
        super(ViewImages, self).build()

        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.IMAGE))
        self.add_configurator('page_qty', PageQtySelector())
        self.add_configurator('scale', ImageZoomSelector(2.0, 0.05, -3.0, 2.0))

        self.image_box = Gtk.Box(visible=True, orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)
        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural')
        self.viewport.connect('size-allocate', self.on_viewport_size_allocate)
        self.viewport.add(self.image_box)
        self.scroller.add(self.viewport)

        self.rebuild_pages()
        self.window.connect('scroll-event', self.on_scroll)
        self.window.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

    def config_changed(self, name: str, value: Any) -> None:
        super(ViewImages, self).config_changed(name, value)
        if name == 'page_qty':
            self.rebuild_pages()
        if name == 'scale':
            self.rescale()
        self.reload()

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

        self.reload()

    def page_activated(self, _sender: Gtk.Widget, page_id: str) -> None:
        self.page_id = page_id
        self.reload()

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def reload(self) -> None:
        if self.document:
            display_ids = self.document.display_id_range(self.page_id, self.page_qty)
            self.pages = []
            for display_id in display_ids:
                self.pages.append(self.document.page_for_id(display_id, self.use_file_group))
        self.redraw()

    def redraw(self) -> None:
        if self.pages:
            box: Gtk.Box
            for box, page in zip_longest(self.image_box.get_children(), self.pages):
                existing_images = {child.get_name():
                                   child for child in box.get_children()}
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
                        image.set_from_stock('missing-image', Gtk.IconSize.DIALOG)
                for child in existing_images.values():
                    child.destroy()
            self.rescale()

    def rescale(self) -> None:
        if self.pages:
            box: Gtk.Box
            scale_config: ImageZoomSelector = self.configurators['scale']
            for box, page in zip_longest(self.image_box.get_children(), self.pages):
                images = {child.get_name():
                          child for child in box.get_children()}
                for i, img in enumerate(page.images if page else [None]):
                    name = 'image_{}'.format(i)
                    image: Gtk.Image
                    image = images[name]
                    if img:
                        thumbnail = pil_scale(img, None, int(scale_config.get_exp() * img.height))
                        image.set_from_pixbuf(pil_to_pixbuf(thumbnail))

    def on_scroll(self, _widget: Gtk.Widget, event: Gdk.EventButton):
        # Handles zoom in / zoom out on Ctrl+mouse wheel
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            release, direction = event.get_scroll_direction()
            if not release:
                return False
            scale_config: ImageZoomSelector = self.configurators['scale']
            adj: Gtk.Adjustment = scale_config.scale.get_adjustment()
            # print(self.scale , adj.get_step_increment())
            if direction == Gdk.ScrollDirection.DOWN:
                scale_config.set_value(self.scale - adj.get_step_increment())
            else:
                scale_config.set_value(self.scale + adj.get_step_increment())
            self.rescale()
            return False
        else:
            # delegate to normal scroll handler (vertical/horizontal navigation)
            return True

    def on_viewport_size_allocate(self, _sender: Gtk.Widget, rect: Gdk.Rectangle) -> None:
        """
        Nothing for now, needed when  we have "fit to width/height"
        """
        pass
