"""First-line text indent normalization helpers."""

from __future__ import annotations

import math

from .units import Auto, Fixed, Percent, parse_size

TextIndentInput = int | float | str


def normalize_text_indent(value: object) -> float | str:
    """Validate and store a first-line text indent value."""

    if isinstance(value, bool):
        raise TypeError("text_indent value must be a number of points or an em string")
    if isinstance(value, (int, float)):
        points = float(value)
        if not math.isfinite(points) or points < 0:
            raise ValueError("text_indent value must be finite and non-negative")
        return points
    if not isinstance(value, str):
        raise TypeError("text_indent value must be a number of points or an em string")

    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("text_indent value must not be empty")
    if normalized.endswith("em"):
        try:
            em = float(normalized[:-2])
        except ValueError as exc:
            raise ValueError("text_indent em value must be numeric") from exc
        if not math.isfinite(em) or em < 0:
            raise ValueError("text_indent em value must be finite and non-negative")
        return normalized
    if normalized.endswith("%"):
        raise ValueError("text_indent does not support percentage values")

    try:
        parsed = parse_size(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unsupported text_indent value: {value}") from exc
    if isinstance(parsed, Percent):
        raise ValueError("text_indent does not support percentage values")
    if isinstance(parsed, Auto):
        raise ValueError("text_indent does not support auto values")
    if not isinstance(parsed, Fixed):
        raise ValueError(f"Unsupported text_indent value: {value}")
    if not math.isfinite(parsed.points) or parsed.points < 0:
        raise ValueError("text_indent value must be finite and non-negative")
    return parsed.points


def resolve_text_indent(value: object, font_size: float) -> float:
    """Resolve a normalized text indent against the effective font size."""

    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        points = float(value)
        return points if math.isfinite(points) and points >= 0 else 0.0
    if isinstance(value, str) and value.endswith("em"):
        try:
            em = float(value[:-2])
        except ValueError:
            return 0.0
        if math.isfinite(em) and em >= 0:
            return em * font_size
    return 0.0
