from gi.repository import Gtk

from ocrd_browser.view import View


class ViewEmpty(View):
    """
    A view of the current PAGE-XML TextEquiv annotation concatenated as plain text
    """
    label: Gtk.Label

    def __init__(self, name: str, window: Gtk.Window):
        super().__init__(name, window)

    def build(self) -> None:
        super().build()

        self.label: Gtk.Label = Gtk.Label(visible=True, vexpand=False)
        self.label.set_text('Hallo')
        self.scroller.add(self.label)
        for id_, view in self.window.view_registry.get_view_options().items():
            menu_item = Gtk.ModelButton(visible=True, centered=False, halign=Gtk.Align.FILL, label=view, hexpand=True)
            menu_item.set_detailed_action_name('win.create_view("{}")'.format(id_))
            self.container.pack_start(menu_item, True, True, 0)
