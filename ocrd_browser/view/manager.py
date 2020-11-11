from typing import Dict, Optional

from gi.repository import Gtk

from .base import View
from .empty import ViewEmpty
from ..model import Document


class ViewManager:

    def __init__(self, window: Gtk.ApplicationWindow, root: Gtk.Box):
        self.window = window
        self.root = root
        self.views: Dict[str, View] = {}

    def set_root_view(self, view_class: type) -> View:
        view = self._create_view(view_class)
        self.connect(self.window, view)
        self.root.add(view.container)
        self.print()
        return view

    def __getitem__(self, view_name: str) -> View:
        if view_name not in self.views:
            raise ValueError('Unknown view: ' + str(view_name))
        return self.views[view_name]

    def close(self, view_name: str) -> None:
        view = self[view_name]
        paned = view.container.get_parent()
        others = [sibling for sibling in paned.get_children() if sibling != view.container]

        if paned is self.root:
            raise ValueError('Not removing root')
        if not isinstance(paned, Gtk.Paned):
            raise ValueError('parent is no Paned but ' + str(type(paned)))
        if len(others) != 1:
            raise ValueError('more than 1 sibling')

        other = others[0]
        parent: Gtk.Container = paned.get_parent()
        paned.remove(view.container)
        paned.remove(other)
        view.container.destroy()
        self.disconnect(self.window, view)

        parent.remove(paned)
        parent.add(other)

        del self.views[view_name]
        del view
        self.print()

    def add(self, new_view_type: Optional[type] = None) -> View:
        new_view_type = new_view_type or ViewEmpty
        return self.split(new_view_type, None, False)

    def split(self, new_view_type: Optional[type] = None, split_view_name: Optional[str] = None, vertical: bool = True) -> View:
        new_view_type = new_view_type or ViewEmpty
        split_view_name = split_view_name or list(self.views.keys())[0]
        view = self[split_view_name]
        parent: Gtk.Box = view.container.get_parent()
        new_pane_root = Gtk.Paned(visible=True, orientation=Gtk.Orientation(vertical), wide_handle=True)
        new_view = self._create_view(new_view_type)
        parent.remove(view.container)
        new_pane_root.add1(view.container)
        new_pane_root.add2(new_view.container)
        parent.add(new_pane_root)
        self.connect(self.window, new_view)
        self.print()
        return new_view

    def replace(self, replace_view: str, new_view_type: type) -> View:
        view = self[replace_view]
        parent: Gtk.Box = view.container.get_parent()
        new_view = self._create_view(new_view_type, replace_view)
        parent.remove(view.container)
        parent.add(new_view.container)
        self.views[view.name] = new_view
        view.container.destroy()
        self.connect(self.window, new_view)
        self.print()
        return new_view

    def _create_view(self, view_class: type, name: Optional[str] = None) -> View:
        name = name or self._unique_name()
        view: View = view_class(name, self.window)
        view.build()
        view.set_document(self.window.document)
        view.page_activated(self.window, self.window.current_page_id)
        self.views[name] = view
        return view

    def set_document(self, document: Document) -> None:
        for view in self.views.values():
            view.set_document(document)

    def update_ui(self) -> None:
        for view in self.views.values():
            view.update_ui()

    def _unique_name(self) -> str:
        for i in range(len(self.views.keys()), 999999):
            name = 'view_' + str(i)
            if name not in self.views:
                return name
        raise RuntimeError('Found no unique view name')

    def disconnect(self, win: Gtk.Window, view: View) -> None:
        try:
            win.disconnect_by_func(view.page_activated)
            win.disconnect_by_func(view.pages_selected)
        except Exception as e:
            print(e)
            pass

    def connect(self, win: Gtk.Window, view: View) -> None:
        win.connect('page_activated', view.page_activated)
        win.connect('pages_selected', view.pages_selected)

    def print(self) -> None:
        print(self.views)
        print(self.print_level())

    def print_level(self, root: Gtk.Paned = None, indent: int = 0) -> str:
        root: Gtk.Container = root or self.root  # type: ignore[no-redef]
        s: str = ('\t' * indent) + root.get_name()
        if isinstance(root, Gtk.Box) and root.get_name().startswith('view_'):
            view = self[root.get_name()]
            s = s + ': ' + type(view).__qualname__ + "\n"
        else:
            s = s + "\n"
            for c in root.get_children():
                if isinstance(c, Gtk.Container):
                    s = s + self.print_level(c, indent + 1)
        return s
