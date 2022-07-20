try:
    import fastentrypoints  # lgtm [py/unused-import]
except ImportError:
    # fastentrypoints is only a performance improvement, ignore
    pass

from setuptools import setup

setup()
