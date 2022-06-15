from .base import View
from .html import ViewHtml
from .images import ViewImages
from .text import ViewText
from .xml import ViewXml
from .empty import ViewEmpty
from .diff import ViewDiff
from .page import ViewPage
from .registry import ViewRegistry


__all__ = ['View', 'ViewRegistry', 'ViewImages', 'ViewText', 'ViewXml', 'ViewHtml', 'ViewEmpty', 'ViewDiff', 'ViewPage']
