"""smart-report package."""

from .builder import Document, DocumentBuilder, document
from .containers.canvas import Canvas
from .containers.frame import Frame
from .containers.table import Table
from .elements.image import Image
from .elements.rich_text import RichText
from .elements.shape import Line, Rect
from .elements.spacer import Spacer
from .elements.text import Text
from .style.font import DEFAULT_FONT_NAME, FontFace, FontFamily, FontRegistry, TextRun, add_fallback_font, add_fallback_font_family, get_default_font_name, get_fallback_font_families, get_fallback_fonts, get_font, get_font_family, register_font, register_font_family, resolve_text_runs, set_default_font, set_default_font_family, set_fallback_font_families, set_fallback_fonts, shaped_string_width, string_width
from .style.typography import shape_text

__version__ = "2.11.12"

__all__ = [
    "Canvas",
    "DEFAULT_FONT_NAME",
    "Document",
    "DocumentBuilder",
    "Frame",
    "FontFace",
    "FontFamily",
    "FontRegistry",
    "Image",
    "Line",
    "Rect",
    "RichText",
    "Spacer",
    "Table",
    "Text",
    "TextRun",
    "add_fallback_font",
    "add_fallback_font_family",
    "document",
    "get_default_font_name",
    "get_fallback_font_families",
    "get_fallback_fonts",
    "get_font",
    "get_font_family",
    "register_font",
    "register_font_family",
    "resolve_text_runs",
    "set_default_font",
    "set_default_font_family",
    "set_fallback_font_families",
    "set_fallback_fonts",
    "shaped_string_width",
    "shape_text",
    "string_width",
]
