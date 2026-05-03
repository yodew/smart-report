"""Style system for smart-report."""

from .font import FontFace, FontRegistry, TextRun, add_fallback_font, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts

__all__ = [
    "FontFace",
    "FontRegistry",
    "TextRun",
    "add_fallback_font",
    "get_fallback_fonts",
    "get_font",
    "register_font",
    "resolve_text_runs",
    "set_default_font",
    "set_fallback_fonts",
]
