"""Style system for smart-report."""

from .font import DEFAULT_FONT_NAME, DEFAULT_FONT_REGISTRY, FontFace, FontRegistry, TextRun, add_fallback_font, get_default_font_name, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts, string_width
from .typography import shape_text

__all__ = [
    "DEFAULT_FONT_NAME",
    "DEFAULT_FONT_REGISTRY",
    "FontFace",
    "FontRegistry",
    "TextRun",
    "add_fallback_font",
    "get_default_font_name",
    "get_fallback_fonts",
    "get_font",
    "register_font",
    "resolve_text_runs",
    "set_default_font",
    "set_fallback_fonts",
    "shape_text",
    "string_width",
]
