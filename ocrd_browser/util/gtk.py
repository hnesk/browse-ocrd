from gi.repository import Gio, GLib, Gtk

from typing import Callable, Dict, Optional, Set, Any

ActionCallback = Optional[Callable[[Gio.SimpleAction, Any], None]]


def print_event(*args: Any, **kwargs: Any) -> None:
    """
    Print out all arguments for event exploration, usage: gtk_widget.connect(gtk_event_name, print_event)
    """
    def nice(e: Any) -> Any:
        if isinstance(e, Gtk.Widget):
            return e.get_path().to_string()
        else:
            return e

    print(list(map(nice, args)), kwargs)


class ActionRegistry:
    def __init__(self, for_widget: Optional[Gio.ActionMap] = None):
        self.for_widget = for_widget if for_widget else Gio.SimpleActionGroup()
        self.actions: Dict[str, Gio.SimpleAction] = {}

    def create(self, name: str, callback: ActionCallback = None,
               param_type: GLib.VariantType = None, state: GLib.Variant = None) -> Gio.SimpleAction:
        callback = callback if callback else getattr(self.for_widget, 'on_' + name)
        action = Gio.SimpleAction(name=name, parameter_type=param_type, state=state)
        if state:
            action.connect("change-state", callback)
        else:
            action.connect("activate", callback)
        self.for_widget.add_action(action)
        self.actions[name] = action
        return action

    def __getitem__(self, item: str) -> Gio.SimpleAction:
        return self.actions[item]


class Callback:
    """
    Wrapper around a callback function with equality by callback function, to be used by WhenIdle
    """
    def __init__(self, callback: Callable, *args: Any, **kwargs: Any):  # type: ignore[type-arg]
        self.priority = kwargs.pop('priority', 100)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def __hash__(self) -> int:
        return hash(self.callback)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Callback) and self.callback == other.callback

    def __call__(self) -> None:
        self.callback(*self.args, **self.kwargs)

    def __str__(self) -> str:
        return '{:03d} {!r}({!r}, {!r})'.format(self.priority, self.callback, self.args, self.kwargs)


class WhenIdle:
    """
    Debouncing wrapper around GLib.idle_add (or another call-later-mechanism) that overwrites prior calls to the same callback

    Also supports priorities, lower priorities get called first

    Usage: see WhenIdle.call
    """
    _instance: 'WhenIdle' = None

    def __init__(self, runner_callback: Callable):  # type: ignore[type-arg]
        self._runner_callback = runner_callback
        self._callbacks: Set[Callback] = set()

    @classmethod
    def instance(cls) -> 'WhenIdle':
        if cls._instance is None:
            cls._instance = cls(GLib.idle_add)
        return cls._instance

    @classmethod
    def call(cls, callback: Callable, *args: Any, **kwargs: Any) -> None:   # type: ignore[type-arg]
        """
        Debouncing wrapper around GLib.idle_add
        Usage:
        > WhenIdle.call(self.redraw, 5, force = True, priority=10)
        will call self.redraw(5, force=True) with priority 10
        """
        cls.instance().add(Callback(callback, *args, **kwargs))

    def add(self, callback: Callback) -> None:
        self._callbacks.add(callback)
        self._runner_callback(self._run)

    def _run(self) -> None:
        if self._callbacks:
            callback = sorted(self._callbacks, key=lambda c: int(c.priority))[0]
            callback()
            self._callbacks.remove(callback)
            self._runner_callback(self._run)
