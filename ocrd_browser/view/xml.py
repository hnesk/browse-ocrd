from gi.repository import GObject, GtkSource, Gtk, Gdk, Pango

from typing import Optional, Tuple, Any

from ocrd_utils.constants import MIMETYPE_PAGE
from ocrd_models.ocrd_page import to_xml

from ocrd_browser.util.launcher import Launcher
from ocrd_browser.view import View
from ocrd_browser.view.base import FileGroupSelector, FileGroupFilter

GObject.type_register(GtkSource.View)


class ViewXml(View):
    """
    A view of the current PAGE-XML with syntax highlighting
    """

    label = 'PAGE-XML'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, MIMETYPE_PAGE)
        self.font_size: Optional[int] = None
        # noinspection PyTypeChecker
        self.text_view: GtkSource.View = None
        # noinspection PyTypeChecker
        self.buffer: GtkSource.Buffer = None

    def build(self) -> None:
        super().build()
        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.XML))
        button = Gtk.Button.new_with_label('PageViewer')
        button.connect('clicked', self.open_jpageviewer)
        button.set_visible(True)
        self.action_bar.pack_start(button)

        lang_manager = GtkSource.LanguageManager()
        style_manager = GtkSource.StyleSchemeManager()

        self.text_view = GtkSource.View(visible=True, vexpand=False, editable=False, monospace=True,
                                        show_line_numbers=True, width_request=400)
        self.buffer = self.text_view.get_buffer()
        self.buffer.set_language(lang_manager.get_language('xml'))
        self.buffer.set_style_scheme(style_manager.get_scheme('tango'))
        self.text_view.connect('scroll-event', self.on_scroll)
        self.scroller.add(self.text_view)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def config_changed(self, name: str, value: Any) -> None:
        super().config_changed(name, value)
        self.reload()

    def open_jpageviewer(self, _button: Gtk.Button) -> None:
        if self.current and self.current.file:
            Launcher().launch('PageViewer', self.document, self.current.file)

    def on_scroll(self, _widget: GtkSource.View, event: Gdk.EventScroll) -> bool:
        # Handles zoom in / zoom out on Ctrl+mouse wheel
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            did_scroll, delta_x, delta_y = event.get_scroll_deltas()
            if did_scroll and abs(delta_y) > 0:
                self.zoom(delta_y)
                return True
        return False

    def zoom(self, direction: float = 0.0) -> None:
        """
        Zoom in or out by direction
        :param direction: amount to zoom

        TODO: make it DRY, currently copy-pasted in ViewText, ViewXml and ViewDiff (maybe as a hidden Configurator)
        """
        style: Gtk.StyleContext = self.text_view.get_style_context()
        font: Pango.FontDescription = style.get_font(style.get_state())
        if self.font_size is None:
            self.font_size = font.get_size()
        size = self.font_size
        size *= (1.2 ** direction)
        if 1 * Pango.SCALE > size or size > 100 * Pango.SCALE:
            return
        self.font_size = int(size)
        font.set_size(size)
        self.text_view.override_font(font)

    def redraw(self) -> None:
        if self.current:
            self.text_view.set_tooltip_text(self.page_id)
            if self.current.file and self.current.file.mimetype == MIMETYPE_PAGE:
                with self.document.path(self.current.file).open('r') as f:
                    text = f.read()
            else:
                text = to_xml(self.current.pc_gts)
            self.buffer.set_text(text)
        else:
            self.buffer.set_text('')
