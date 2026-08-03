"""Text wrapping helpers shared by layout and rendering."""

from __future__ import annotations

from typing import Protocol

from ..style.font import shaped_string_width, string_width as fallback_string_width
from ..style.typography import TextDirection, TypographyMode, shape_text_for_width


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


def wrap_text(
    text: str,
    width: float,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn | None = None,
    typography: TypographyMode = "plain",
    text_direction: TextDirection = "auto",
    letter_spacing: float = 0.0,
    text_indent: float = 0.0,
) -> list[str]:
    if not text:
        return [""]

    measure = string_width or _string_width_fn()
    lines: list[str] = []
    safe_width = max(1.0, width)
    first_line_width = max(1.0, safe_width - max(0.0, text_indent))
    is_first_line = True

    for paragraph in text.splitlines() or [text]:
        if not paragraph.strip():
            lines.append("")
            is_first_line = False
            continue
        paragraph_lines = _wrap_paragraph(
            paragraph,
            first_line_width if is_first_line else safe_width,
            safe_width,
            font_name,
            font_size,
            measure,
            typography,
            text_direction,
            letter_spacing,
        )
        lines.extend(paragraph_lines)
        is_first_line = False

    return lines or [""]


def _wrap_paragraph(
    paragraph: str,
    first_line_width: float,
    width: float,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float,
) -> list[str]:
    tokens = _tokens(paragraph)
    lines: list[str] = []
    current = ""
    current_width = first_line_width

    for token in tokens:
        if token.isspace() and not current:
            continue
        candidate = f"{current}{token}"
        if _string_width(candidate.rstrip(), font_name, font_size, string_width, typography, text_direction, letter_spacing) <= current_width:
            current = candidate
            continue
        if current.strip():
            current, token = _rebalance_for_line_break(current.rstrip(), token)
            lines.append(current.rstrip())
            current_width = width
            current = token.lstrip()
            if not current:
                continue
            if _string_width(current, font_name, font_size, string_width, typography, text_direction, letter_spacing) <= current_width:
                continue
        else:
            current = token.lstrip()
        if _string_width(current, font_name, font_size, string_width, typography, text_direction, letter_spacing) > current_width:
            split_parts = _split_long_token(current, current_width, width, font_name, font_size, string_width, typography, text_direction, letter_spacing)
            lines.extend(split_parts[:-1])
            current = split_parts[-1] if split_parts else ""
            if split_parts[:-1]:
                current_width = width

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


def _rebalance_for_line_break(current: str, next_token: str) -> tuple[str, str]:
    while current and next_token and _cannot_start_line(next_token[0]):
        next_token = f"{current[-1]}{next_token}"
        current = current[:-1]
    while current and _cannot_end_line(current[-1]) and next_token:
        next_token = f"{current[-1]}{next_token}"
        current = current[:-1]
    return current, next_token


def _cannot_start_line(character: str) -> bool:
    return character in "，。！？；：、）】》〉」』”’)]}.,!?:;"


def _cannot_end_line(character: str) -> bool:
    return character in "（【《〈「『“‘([{"


def _split_long_token(
    token: str,
    first_part_width: float,
    width: float,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float,
) -> list[str]:
    parts: list[str] = []
    current = ""
    current_width = first_part_width
    for character in token:
        candidate = f"{current}{character}"
        if current and _string_width(candidate, font_name, font_size, string_width, typography, text_direction, letter_spacing) > current_width:
            parts.append(current)
            current = character
            current_width = width
            continue
        current = candidate
    if current:
        parts.append(current)
    return parts or [""]


def _string_width_fn() -> StringWidthFn:
    return fallback_string_width


def _string_width(
    text: str,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn,
    typography: TypographyMode,
    text_direction: TextDirection,
    letter_spacing: float = 0.0,
) -> float:
    base_width: float
    if typography == "advanced":
        base_width = shaped_string_width(text, font_name, font_size)
    else:
        base_width = string_width(shape_text_for_width(text, typography, text_direction), font_name, font_size)
    return base_width + max(0, len(text) - 1) * letter_spacing


def text_width(
    text: str,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn | None = None,
    typography: TypographyMode = "plain",
    text_direction: TextDirection = "auto",
    letter_spacing: float = 0.0,
) -> float:
    return _string_width(text, font_name, font_size, string_width or _string_width_fn(), typography, text_direction, letter_spacing)
