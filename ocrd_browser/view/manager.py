from typing import Dict, Optional, List

from gi.repository import Gtk

from .base import View
from .empty import ViewEmpty
from ..model import Document


class ViewManager:

    def __init__(self, window: Gtk.ApplicationWindow, root: Gtk.Box):
        self.window = window
        self.root = root
        self.views: Dict[str, View] = {}

    def add(self, view_class):
        view = self.create_view(view_class)
        self.connect_view(view)
        pass

    def close(self, view_name: str):
        view = self.views.get(view_name, None)
        if not view:
            raise ValueError('Unknown view: '+view_name)
        view.container.destroy()
        self.window.disconnect_by_func(view.page_activated)
        del self.views[view_name]
        del view

    def split(self, view_name: str):
        view = self.views.get(view_name, None)
        if not view:
            raise ValueError('Unknown view: '+view_name)

        parent: Gtk.Box = view.container.get_parent()
        new_pane_root = Gtk.Paned(visible=True)
        empty_view = self.create_view(ViewEmpty)
        parent.remove(view.container)
        new_pane_root.add1(view.container)
        new_pane_root.add2(empty_view.container)
        parent.add(new_pane_root)
        self.window.connect('page_activated', empty_view.page_activated)
        self.window.page_list.connect('pages_selected', empty_view.pages_selected)

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
        self.window.page_list.connect('pages_selected', view.pages_selected)
        self.root.add(view.container)
        #self.root.pack_start(view.container, True, True, 3)

    def set_document(self, document: Document):
        for view in self.views.values():
            view.set_document(document)

    def update_ui(self):
        for view in self.views.values():
            view.update_ui()
