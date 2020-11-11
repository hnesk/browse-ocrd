from typing import Optional

from gi.repository import Gtk

from ocrd_browser.view import View


class ViewEmpty(View):
    """
    A view of the current PAGE-XML TextEquiv annotation concatenated as plain text
    """
    label: Gtk.Label

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)
        self.viewport: Optional[Gtk.Viewport] = None
        self.box: Optional[Gtk.Box] = None

    def build(self) -> None:
        super().build()
        self.viewport = Gtk.Viewport(visible=True, hscroll_policy='natural', vscroll_policy='natural',
                                     parent=self.scroller)
        self.box = Gtk.Box(visible=True, parent=self.viewport, orientation=Gtk.Orientation.VERTICAL)
        self.label: Gtk.Label = Gtk.Label(visible=True, vexpand=False)
        self.label.set_text('Create New View:')
        self.box.pack_start(self.label, False, False, 0)
        for id_, view in self.window.view_registry.get_view_options().items():
            menu_item = Gtk.ModelButton(visible=True, centered=False, halign=Gtk.Align.FILL, label=view, hexpand=True)
            menu_item.set_detailed_action_name('win.replace_view(("{}", "{}"))'.format(self.name, id_))
            self.box.pack_start(menu_item, False, False, 0)
