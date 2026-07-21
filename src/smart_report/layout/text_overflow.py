"""Plain text overflow helpers shared by Text and table cells."""

from __future__ import annotations

from .text_wrap import StringWidthFn, text_width, wrap_text
from ..style.typography import TextDirection, TypographyMode

TEXT_OVERFLOW_VALUES = {"wrap", "clip", "ellipsis"}


def normalize_text_overflow(value: str, *, label: str = "text") -> str:
    lowered = value.lower()
    if lowered in TEXT_OVERFLOW_VALUES:
        return lowered
    raise ValueError(f"Unsupported {label} text overflow: {value}")


def normalize_plain_overflow_text(text: str) -> str:
    return " ".join(text.splitlines())


def plain_overflow_text_width(
    text: str,
    font_name: str,
    font_size: float,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float = 0.0,
    string_width: StringWidthFn | None = None,
) -> float:
    return text_width(
        normalize_plain_overflow_text(text),
        font_name,
        font_size,
        string_width,
        typography,
        text_direction,
        letter_spacing,
    )


def fit_plain_overflow_text(
    text: str,
    width: float,
    font_name: str,
    font_size: float,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float = 0.0,
    string_width: StringWidthFn | None = None,
    force_ellipsis: bool = False,
) -> str:
    normalized = normalize_plain_overflow_text(text)
    if not force_ellipsis and plain_overflow_text_width(normalized, font_name, font_size, typography, text_direction, letter_spacing, string_width) <= width:
        return normalized
    ellipsis = "…"
    if text_width(ellipsis, font_name, font_size, string_width, typography, text_direction, letter_spacing) > width:
        return ""
    low = 0
    high = len(normalized)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        prefix = normalized[:mid].rstrip()
        candidate = f"{prefix}{ellipsis}" if prefix else ellipsis
        candidate_width = text_width(candidate, font_name, font_size, string_width, typography, text_direction, letter_spacing)
        if candidate_width <= width:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best


def fit_multiline_overflow_text(
    text: str,
    width: float,
    height: float,
    line_height: float,
    font_name: str,
    font_size: float,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float = 0.0,
    string_width: StringWidthFn | None = None,
) -> list[str]:
    wrapped_lines = wrap_text(
        text,
        width,
        font_name,
        font_size,
        string_width,
        typography,
        text_direction,
        letter_spacing,
    )
    max_lines = max(1, int(max(0.0, height) // max(1.0, line_height)))
    if len(wrapped_lines) <= max_lines:
        return wrapped_lines
    visible_lines = list(wrapped_lines[:max_lines])
    visible_lines[-1] = fit_plain_overflow_text(
        visible_lines[-1],
        width,
        font_name,
        font_size,
        typography,
        text_direction,
        letter_spacing,
        string_width,
        True,
    )
    return visible_lines
