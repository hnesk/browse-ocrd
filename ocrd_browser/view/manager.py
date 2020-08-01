from pkg_resources import EntryPoint, iter_entry_points
from typing import Dict
from .base import View


class ViewManager:
    def __init__(self, views: Dict):
        self.views = views

    @classmethod
    def create_from_entry_points(cls) -> 'ViewManager':
        views = {}
        entry_point: EntryPoint
        for entry_point in iter_entry_points('ocrd_browser_view'):
            view_class = entry_point.load()
            assert issubclass(view_class, View)
            views[entry_point.name] = view_class
        return cls(views)

    def get_view_options(self) -> Dict:
        return {id_: view_class.__name__ for id_, view_class in self.views.items()}

    def get_view(self, id_):
        return self.views[id_] if id_ in self.views else None
