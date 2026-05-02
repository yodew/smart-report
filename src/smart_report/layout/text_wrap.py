"""Text wrapping helpers shared by layout and rendering."""

from __future__ import annotations

from importlib import import_module
from typing import Protocol, cast


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


def wrap_text(text: str, width: float, font_name: str, font_size: float, string_width: StringWidthFn | None = None) -> list[str]:
    if not text:
        return [""]

    measure = string_width or _string_width_fn()
    lines: list[str] = []
    safe_width = max(1.0, width)

    for paragraph in text.splitlines() or [text]:
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(_wrap_paragraph(paragraph, safe_width, font_name, font_size, measure))

    return lines or [""]


def _wrap_paragraph(paragraph: str, width: float, font_name: str, font_size: float, string_width: StringWidthFn) -> list[str]:
    tokens = _tokens(paragraph)
    lines: list[str] = []
    current = ""

    for token in tokens:
        if token.isspace() and not current:
            continue
        candidate = f"{current}{token}"
        if string_width(candidate.rstrip(), font_name, font_size) <= width:
            current = candidate
            continue
        if current.strip():
            lines.append(current.rstrip())
            current = token.lstrip()
            if not current:
                continue
            if string_width(current, font_name, font_size) <= width:
                continue
        else:
            current = token.lstrip()
        if string_width(current, font_name, font_size) > width:
            split_parts = _split_long_token(current, width, font_name, font_size, string_width)
            lines.extend(split_parts[:-1])
            current = split_parts[-1] if split_parts else ""

    if current.strip():
        lines.append(current.rstrip())
    return lines or [""]


def _tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current = ""
    for character in text:
        if character.isspace():
            if current:
                tokens.append(current)
                current = ""
            tokens.append(" ")
            continue
        if _is_cjk_or_punctuation(character):
            if current:
                tokens.append(current)
                current = ""
            tokens.append(character)
            continue
        current += character
    if current:
        tokens.append(current)
    return tokens


def _is_cjk_or_punctuation(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x2E80 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0xFF00 <= codepoint <= 0xFFEF
        or character in "，。！？；：、（）《》〈〉“”‘’—…"
    )


def _split_long_token(token: str, width: float, font_name: str, font_size: float, string_width: StringWidthFn) -> list[str]:
    parts: list[str] = []
    current = ""
    for character in token:
        candidate = f"{current}{character}"
        if current and string_width(candidate, font_name, font_size) > width:
            parts.append(current)
            current = character
            continue
        current = candidate
    if current:
        parts.append(current)
    return parts or [""]


def _string_width_fn() -> StringWidthFn:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    return cast(StringWidthFn, getattr(pdfmetrics, "stringWidth"))
