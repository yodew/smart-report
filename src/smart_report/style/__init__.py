"""Style system for smart-report."""

from .font import DEFAULT_FONT_NAME, DEFAULT_FONT_REGISTRY, FontFace, FontFamily, FontRegistry, TextRun, add_fallback_font, add_fallback_font_family, get_default_font_name, get_fallback_font_families, get_fallback_fonts, get_font, get_font_family, register_font, register_font_family, resolve_text_runs, set_default_font, set_default_font_family, set_fallback_font_families, set_fallback_fonts, shaped_string_width, string_width
from .typography import shape_text

__all__ = [
    "DEFAULT_FONT_NAME",
    "DEFAULT_FONT_REGISTRY",
    "FontFace",
    "FontFamily",
    "FontRegistry",
    "TextRun",
    "add_fallback_font",
    "add_fallback_font_family",
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
