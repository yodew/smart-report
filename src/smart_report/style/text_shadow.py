"""Text shadow normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from .color import RGBA, parse_color


@dataclass(frozen=True, slots=True)
class TextShadow:
    """Block-level text shadow paint settings."""

    x: float = 0.0
    y: float = 0.0
    blur: float = 0.0
    spread: float = 0.0
    color: RGBA = RGBA(0.0, 0.0, 0.0, 1.0)
    method: Literal["stroke", "gaussian"] = "stroke"
    sigma: float = 0
    dpi: float = 300
    knockout: bool = False


def normalize_text_shadow(
    x: object = 0,
    y: object = 0,
    blur: object = 0,
    spread: object = 0,
    color: str | RGBA = "#000000",
    *,
    method: Literal["stroke", "gaussian"] = "stroke",
    sigma: float | None = None,
    dpi: float = 300,
    knockout: bool = False,
) -> TextShadow:
    """Validate and normalize block-level text shadow settings."""

    shadow_x = _finite_float(x, "x")
    shadow_y = _finite_float(y, "y")
    shadow_blur = _non_negative_finite_float(blur, "blur")
    shadow_spread = _non_negative_finite_float(spread, "spread")
    parsed_color = parse_color(color)
    if parsed_color is None:
        raise TypeError("text_shadow color must not be None")
    if method not in {"stroke", "gaussian"}:
        raise ValueError(f"Unsupported text shadow method: {method}")
    if method == "gaussian" and (sigma is None or shadow_blur != 0):
        raise ValueError("Gaussian text shadows require sigma and blur=0")
    if method == "stroke" and sigma is not None:
        raise ValueError("sigma requires method=gaussian")
    if knockout and method != "gaussian":
        raise ValueError("knockout requires method=gaussian")
    normalized_sigma = _non_negative_finite_float(sigma if sigma is not None else 0, "sigma")
    normalized_dpi = _non_negative_finite_float(dpi, "dpi")
    if normalized_dpi == 0:
        raise ValueError("text_shadow dpi must be > 0")
    return TextShadow(shadow_x, shadow_y, shadow_blur, shadow_spread, parsed_color,
                      method, normalized_sigma, normalized_dpi, knockout)


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
