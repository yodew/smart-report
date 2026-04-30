"""Unit parsing and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

POINTS_PER_INCH = 72.0
POINTS_PER_MM = POINTS_PER_INCH / 25.4
POINTS_PER_CM = POINTS_PER_MM * 10


@dataclass(frozen=True, slots=True)
class Fixed:
    """Absolute size in PDF points."""

    points: float


@dataclass(frozen=True, slots=True)
class Percent:
    """Size relative to a containing block."""

    ratio: float


@dataclass(frozen=True, slots=True)
class Auto:
    """Content-driven size."""


SizeSpec: TypeAlias = Fixed | Percent | Auto
SizeInput: TypeAlias = SizeSpec | str | int | float | None


AUTO = Auto()


def fixed(points: float) -> Fixed:
    return Fixed(float(points))


def percent(ratio: float) -> Percent:
    return Percent(float(ratio))


def parse_size(value: SizeInput) -> SizeSpec:
    if isinstance(value, (Fixed, Percent, Auto)):
        return value

    if value is None:
        return AUTO

    if isinstance(value, (int, float)):
        return Fixed(float(value))

    normalized = value.strip().lower()
    if normalized == "auto":
        return AUTO
    if normalized.endswith("%"):
        return Percent(float(normalized[:-1]) / 100.0)
    if normalized.endswith("pt"):
        return Fixed(float(normalized[:-2]))
    if normalized.endswith("mm"):
        return Fixed(float(normalized[:-2]) * POINTS_PER_MM)
    if normalized.endswith("cm"):
        return Fixed(float(normalized[:-2]) * POINTS_PER_CM)
    if normalized.endswith("in"):
        return Fixed(float(normalized[:-2]) * POINTS_PER_INCH)

    return Fixed(float(normalized))


def resolve_size(value: SizeSpec, reference: float | None, auto_value: float = 0.0) -> float:
    if isinstance(value, Fixed):
        return value.points
    if isinstance(value, Percent):
        if reference is None:
            return auto_value
        return reference * value.ratio
    return auto_value


def is_auto(value: SizeSpec) -> bool:
    return isinstance(value, Auto)
