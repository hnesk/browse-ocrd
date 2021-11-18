from gi.repository import GObject, GtkSource, Gtk, Gdk

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
                                        show_line_numbers=True,
                                        width_request=400)
        self.buffer = self.text_view.get_buffer()
        self.buffer.set_language(lang_manager.get_language('xml'))
        self.buffer.set_style_scheme(style_manager.get_scheme('tango'))

        eventbox = Gtk.EventBox(visible=True)
        eventbox.add_events(Gdk.EventMask.SMOOTH_SCROLL_MASK)
        eventbox.connect('scroll-event', self.on_scroll)
        eventbox.add(self.text_view)

        self.scroller.add(eventbox)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def config_changed(self, name: str, value: Any) -> None:
        super().config_changed(name, value)
        self.reload()

    def open_jpageviewer(self, _button: Gtk.Button) -> None:
        if self.current and self.current.file:
            Launcher().launch('PageViewer', self.document, self.current.file)

    def on_scroll(self, _widget: Gtk.EventBox, event: Gdk.EventScroll) -> bool:
        # Handles zoom in / zoom out on Ctrl+mouse wheel
        accel_mask = Gtk.accelerator_get_default_mod_mask()
        if event.state & accel_mask == Gdk.ModifierType.CONTROL_MASK:
            did_scroll, delta_x, delta_y = event.get_scroll_deltas()
            if did_scroll and abs(delta_y) > 0:
                self.zoom(delta_y > 0)
                return True
        return False

    def zoom(self, direction: bool = True) -> None:
        style = self.text_view.get_style_context()
        font = style.get_font(style.get_state())
        size = font.get_size()
        if direction:
            size *= 1.2
        else:
            size /= 1.2
        font.set_size(size)
        # gives a different figure: print(style.get_property('font-size', style.get_state()))
        # says it does not have that property: print(style.set_property('font-size', 20)
        # deprecated, but works:
        self.text_view.modify_font(font)

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
