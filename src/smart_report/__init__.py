"""smart-report package."""

from .builder import Document, DocumentBuilder, document
from .containers.canvas import Canvas
from .containers.frame import Frame
from .containers.table import Table
from .elements.image import Image
from .elements.shape import Line, Rect
from .elements.spacer import Spacer
from .elements.text import Text
from .style.font import FontFace, FontRegistry, get_font, register_font, set_default_font

__version__ = "0.4.0"

__all__ = [
    "Canvas",
    "Document",
    "DocumentBuilder",
    "Frame",
    "FontFace",
    "FontRegistry",
    "Image",
    "Line",
    "Rect",
    "Spacer",
    "Table",
    "Text",
    "document",
    "get_font",
    "register_font",
    "set_default_font",
]
