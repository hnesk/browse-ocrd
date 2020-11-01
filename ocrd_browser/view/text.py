from gi.repository import GObject, GtkSource, Gtk

from typing import Optional, Tuple, Any

from ocrd_utils.constants import MIMETYPE_PAGE
from ocrd_browser.view import View
from ocrd_browser.view.base import FileGroupSelector, FileGroupFilter

GObject.type_register(GtkSource.View)


class ViewText(View):
    """
    A view of the current PAGE-XML TextEquiv annotation concatenated as plain text
    """

    label = 'Text'

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, MIMETYPE_PAGE)
        # noinspection PyTypeChecker
        self.text_view: GtkSource.View = None
        # noinspection PyTypeChecker
        self.buffer: GtkSource.Buffer = None

    def build(self) -> None:
        super().build()
        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))

        self.text_view = GtkSource.View(visible=True, vexpand=False, editable=False,
                                        monospace=False,
                                        show_line_numbers=True,
                                        width_request=400)
        self.buffer = self.text_view.get_buffer()

        self.scroller.add(self.text_view)

    @property
    def use_file_group(self) -> str:
        return self.file_group[0]

    def config_changed(self, name: str, value: Any) -> None:
        super().config_changed(name, value)
        self.reload()

    def redraw(self) -> None:
        if self.current:
            self.text_view.set_tooltip_text(self.page_id)
            regions = self.current.pc_gts.get_Page().get_AllRegions(classes=['Text'], order='reading-order')
            text = ''
            for i, region in enumerate(regions):
                if i:
                    text += '\n'  # or line feed?
                if region.get_TextEquiv() and region.get_TextEquiv()[0].Unicode:
                    text += region.get_TextEquiv()[0].Unicode
                    continue
                lines = region.get_TextLine()
                for j, line in enumerate(lines):
                    if j:
                        text += '\n'
                    if line.get_TextEquiv() and line.get_TextEquiv()[0].Unicode:
                        text += line.get_TextEquiv()[0].Unicode
                        continue
                    words = line.get_Word()
                    for k, word in enumerate(words):
                        if k:
                            text += ' '
                        if word.get_TextEquiv() and word.get_TextEquiv()[0].Unicode:
                            text += word.get_TextEquiv()[0].Unicode
                            continue
                        glyphs = word.get_Glyph()
                        for l, glyph in enumerate(glyphs): # noqa E741
                            if glyph.get_TextEquiv() and glyph.get_TextEquiv()[0].Unicode:
                                text += glyph.get_TextEquiv()[0].Unicode

            self.buffer.set_text(text)
        else:
            self.buffer.set_text('')
