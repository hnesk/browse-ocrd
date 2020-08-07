from typing import Any, Optional, Tuple

from gi.repository import GObject, GtkSource

from ocrd_utils.constants import MIMETYPE_PAGE
from ocrd_models.ocrd_page import to_xml
from ocrd_browser.view import View
from ocrd_browser.view.base import FileGroupSelector, FileGroupFilter

GObject.type_register(GtkSource.View)


class ViewXml(View):
    """
    A view of the current PAGE-XML with syntax highlighting
    """

    label = 'PAGE-XML'

    def __init__(self, name, window, **kwargs):
        super().__init__(name, window, **kwargs)
        self.file_group: Tuple[Optional[str], Optional[str]] = (None, MIMETYPE_PAGE)
        self.text_view: GtkSource.View = None
        self.buffer: GtkSource.Buffer = None

    def build(self):
        super().build()
        self.add_configurator('file_group', FileGroupSelector(FileGroupFilter.PAGE))

        lang_manager = GtkSource.LanguageManager()
        style_manager = GtkSource.StyleSchemeManager()

        self.text_view = GtkSource.View(visible=True, vexpand=False, editable=False, monospace=True,
                                        show_line_numbers=True,
                                        width_request=400)
        self.buffer: GtkSource.Buffer = self.text_view.get_buffer()
        self.buffer.set_language(lang_manager.get_language('xml'))
        self.buffer.set_style_scheme(style_manager.get_scheme('tango'))

        self.viewport.add(self.text_view)

    @property
    def use_file_group(self):
        return self.file_group[0]

    def config_changed(self, name, value):
        super().config_changed(name, value)
        self.reload()

    def redraw(self) -> None:
        if self.current:
            text = to_xml(self.current.pc_gts)
            # TODO: Crashes with big XML, as a workaround shorten the file
            if len(text) > 50000:
                self.buffer.set_highlight_syntax(False)
                line_break_start = text.find("\n", 45000)
                line_break_end = text.find("\n", len(text) - 5000)

                text = text[:line_break_start] + "\n\n\n" + \
                       "... I'm sorry Dave, I'm afraid I can't do that ...\n" + \
                       "... With bigger XML files there are frequent crashes ...\n\n" + \
                       text[line_break_end:]

            else:
                self.buffer.set_highlight_syntax(True)

            self.buffer.set_text(text)
