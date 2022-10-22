from __future__ import annotations
from typing import Dict, Tuple, Optional, Type
from .base import View

from importlib_metadata import entry_points

ViewInfo = Tuple[type, str, str]


class ViewRegistry:
    def __init__(self, views: Dict[str, ViewInfo]):
        self.views = views

    @classmethod
    def create_from_entry_points(cls) -> ViewRegistry:
        views = {}
        # also loads view plugins, e.g. from browse-ocrd-physical-import
        for entry_point in entry_points(group='ocrd_browser_view'):
            view_class = entry_point.load()
            assert issubclass(view_class, View)
            label = view_class.label if hasattr(view_class, 'label') else view_class.__name__
            description = view_class.__doc__.strip()
            views[entry_point.name] = (view_class, label, description)
        return cls(views)

    def get_view_options(self) -> Dict[str, str]:
        return {id_: label for id_, (view_class, label, description) in self.views.items()}

    def get_view(self, id_: str) -> Optional[Type[View]]:
        return self.views[id_][0] if id_ in self.views else None
