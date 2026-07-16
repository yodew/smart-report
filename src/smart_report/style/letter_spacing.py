"""Letter-spacing normalization and resolution helpers."""

from __future__ import annotations

import math

LetterSpacingInput = str | int | float


def normalize_letter_spacing(value: LetterSpacingInput) -> str | float:
    """Normalize a letter-spacing value while preserving relative units."""

    if isinstance(value, (int, float)):
        points = float(value)
        if not math.isfinite(points):
            raise ValueError("letter spacing must be finite")
        return points
    normalized = value.strip().lower()
    if normalized.endswith("em"):
        factor = float(normalized[:-2])
        if not math.isfinite(factor):
            raise ValueError("letter spacing must be finite")
        return normalized
    if normalized.endswith("%"):
        percent = float(normalized[:-1])
        if not math.isfinite(percent):
            raise ValueError("letter spacing must be finite")
        return normalized
    points = float(normalized)
    if not math.isfinite(points):
        raise ValueError("letter spacing must be finite")
    return points


def resolve_letter_spacing(value: object, font_size: float) -> float:
    """Resolve a normalized letter-spacing value to points."""

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if value.endswith("em"):
            return float(value[:-2]) * font_size
        if value.endswith("%"):
            return (float(value[:-1]) / 100.0) * font_size
    return 0.0
