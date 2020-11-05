from typing import Dict

from gi.repository import Gtk

from .base import View
from .empty import ViewEmpty
from ..model import Document


class ViewManager:

    def __init__(self, window: Gtk.ApplicationWindow, root: Gtk.Box):
        self.window = window
        self.root = root
        self.views: Dict[str, View] = {}

    def add(self, view_class: type) -> View:
        view = self.create_view(view_class)
        self.connect_view(view)
        return view

    def __getitem__(self, view_name: str) -> View:
        if view_name not in self.views:
            raise ValueError('Unknown view: ' + view_name)
        return self.views[view_name]

    def close(self, view_name: str) -> None:
        view = self[view_name]
        view.container.destroy()
        try:
            self.window.disconnect_by_func(view.page_activated)
            self.window.disconnect_by_func(view.pages_selected)
        except Exception as e:
            print(e)
            pass

        del self.views[view_name]
        del view

    def split(self, view_name: str) -> View:
        view = self[view_name]
        parent: Gtk.Box = view.container.get_parent()
        new_pane_root = Gtk.Paned(visible=True)
        empty_view = self.create_view(ViewEmpty)
        parent.remove(view.container)
        new_pane_root.add1(view.container)
        new_pane_root.add2(empty_view.container)
        parent.add(new_pane_root)
        self.window.connect('page_activated', empty_view.page_activated)
        #self.window.connect('pages_selected', empty_view.pages_selected)
        return empty_view

    def add_view(self, view_class: type) -> None:
        view = self.create_view(view_class)
        self.connect_view(view)

    def create_view(self, view_class: type) -> View:
        name = 'view_{}'.format(len(self.views.keys()))
        view: View = view_class(name, self.window)
        view.build()
        view.set_document(self.window.document)
        view.page_activated(self.window, self.window.current_page_id)
        self.views[name] = view
        return view

    def connect_view(self, view: View) -> None:
        self.window.connect('page_activated', view.page_activated)
        self.window.connect('pages_selected', view.pages_selected)
        self.root.add(view.container)

    def set_document(self, document: Document) -> None:
        for view in self.views.values():
            view.set_document(document)

    def update_ui(self) -> None:
        for view in self.views.values():
            view.update_ui()
