try:
    import fastentrypoints  # lgtm [py/unused-import] # noqa: F401
except ImportError:
    # fastentrypoints is only a performance improvement, ignore
    pass

from setuptools import setup

setup()
