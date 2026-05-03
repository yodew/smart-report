"""smart-report package."""

from .builder import Document, DocumentBuilder, document
from .containers.canvas import Canvas
from .containers.frame import Frame
from .containers.table import Table
from .elements.image import Image
from .elements.shape import Line, Rect
from .elements.spacer import Spacer
from .elements.text import Text
from .style.font import FontFace, FontRegistry, TextRun, add_fallback_font, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts

__version__ = "0.8.0"

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
    "TextRun",
    "add_fallback_font",
    "document",
    "get_fallback_fonts",
    "get_font",
    "register_font",
    "resolve_text_runs",
    "set_default_font",
    "set_fallback_fonts",
]
