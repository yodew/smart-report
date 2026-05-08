"""Typography shaping helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Callable, Literal, cast

TypographyMode = Literal["plain", "auto"]
TextDirection = Literal["auto", "ltr", "rtl"]

VALID_TYPOGRAPHY_MODES = {"plain", "auto"}
VALID_TEXT_DIRECTIONS = {"auto", "ltr", "rtl"}

ArabicReshapeFn = Callable[[str], str]
BidiDisplayFn = Callable[..., str]


def normalize_typography_mode(value: str) -> TypographyMode:
    normalized = value.lower()
    if normalized not in VALID_TYPOGRAPHY_MODES:
        raise ValueError(f"Unsupported typography mode: {value}")
    return cast(TypographyMode, normalized)


def normalize_text_direction(value: str) -> TextDirection:
    normalized = value.lower()
    if normalized not in VALID_TEXT_DIRECTIONS:
        raise ValueError(f"Unsupported text direction: {value}")
    return cast(TextDirection, normalized)


def shape_text(text: str, mode: TypographyMode = "plain", direction: TextDirection = "auto") -> str:
    if not text or mode == "plain":
        return text

    reshaped = _reshape_arabic_text(text) if _contains_arabic(text) else text
    if direction == "rtl" or _contains_rtl_text(reshaped):
        return _bidi_display(reshaped, direction)
    return reshaped


def shape_text_for_width(text: str, mode: TypographyMode = "plain", direction: TextDirection = "auto") -> str:
    return shape_text(text, mode, direction)


def _reshape_arabic_text(text: str) -> str:
    arabic_reshaper = import_module("arabic_reshaper")
    reshape = cast(ArabicReshapeFn, getattr(arabic_reshaper, "reshape"))
    return reshape(text)


def _bidi_display(text: str, direction: TextDirection) -> str:
    bidi_algorithm = import_module("bidi.algorithm")
    get_display = cast(BidiDisplayFn, getattr(bidi_algorithm, "get_display"))
    if direction == "rtl":
        return get_display(text, base_dir="R")
    if direction == "ltr":
        return get_display(text, base_dir="L")
    return get_display(text)


def _contains_arabic(text: str) -> bool:
    return any(_is_arabic_codepoint(ord(character)) for character in text)


def _contains_rtl_text(text: str) -> bool:
    return any(_is_rtl_codepoint(ord(character)) for character in text)


def _is_arabic_codepoint(codepoint: int) -> bool:
    return (
        0x0600 <= codepoint <= 0x06FF
        or 0x0750 <= codepoint <= 0x077F
        or 0x08A0 <= codepoint <= 0x08FF
        or 0xFB50 <= codepoint <= 0xFDFF
        or 0xFE70 <= codepoint <= 0xFEFF
    )


def _is_rtl_codepoint(codepoint: int) -> bool:
    return (
        0x0590 <= codepoint <= 0x08FF
        or 0xFB1D <= codepoint <= 0xFDFF
        or 0xFE70 <= codepoint <= 0xFEFF
    )


__all__ = [
    "TextDirection",
    "TypographyMode",
    "normalize_text_direction",
    "normalize_typography_mode",
    "shape_text",
    "shape_text_for_width",
]
