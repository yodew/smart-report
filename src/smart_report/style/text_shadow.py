"""Text shadow normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .color import RGBA, parse_color


@dataclass(frozen=True, slots=True)
class TextShadow:
    """Block-level text shadow paint settings."""

    x: float = 0.0
    y: float = 0.0
    blur: float = 0.0
    spread: float = 0.0
    color: RGBA = RGBA(0.0, 0.0, 0.0, 1.0)


def normalize_text_shadow(
    x: object = 0,
    y: object = 0,
    blur: object = 0,
    spread: object = 0,
    color: str | RGBA = "#000000",
) -> TextShadow:
    """Validate and normalize block-level text shadow settings."""

    shadow_x = _finite_float(x, "x")
    shadow_y = _finite_float(y, "y")
    shadow_blur = _non_negative_finite_float(blur, "blur")
    shadow_spread = _non_negative_finite_float(spread, "spread")
    parsed_color = parse_color(color)
    if parsed_color is None:
        raise TypeError("text_shadow color must not be None")
    return TextShadow(shadow_x, shadow_y, shadow_blur, shadow_spread, parsed_color)


def _finite_float(value: object, name: str) -> float:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"text_shadow {name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"text_shadow {name} must be finite")
    return result


def _non_negative_finite_float(value: object, name: str) -> float:
    result = _finite_float(value, name)
    if result < 0:
        raise ValueError(f"text_shadow {name} must be >= 0")
    return result


__all__ = ["TextShadow", "normalize_text_shadow"]
