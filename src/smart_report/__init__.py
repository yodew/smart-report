"""smart-report package."""

from .builder import Document, DocumentBuilder, document
from .containers.canvas import Canvas
from .containers.frame import Frame
from .containers.table import Table
from .elements.image import Image
from .elements.shape import Line, Rect
from .elements.spacer import Spacer
from .elements.text import Text
from .style.font import DEFAULT_FONT_NAME, FontFace, FontRegistry, TextRun, add_fallback_font, get_default_font_name, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts, string_width

__version__ = "1.2.0"

__all__ = [
    "Canvas",
    "DEFAULT_FONT_NAME",
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
    "get_default_font_name",
    "get_fallback_fonts",
    "get_font",
    "register_font",
    "resolve_text_runs",
    "set_default_font",
    "set_fallback_fonts",
    "string_width",
]
