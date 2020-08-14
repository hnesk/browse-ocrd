DEFAULT_FILE_GROUP = 'OCR-D-IMG'

from .page import Page           # noqa E402
from .document import Document   # noqa E402

__all__ = ['Page', 'Document', 'DEFAULT_FILE_GROUP']
