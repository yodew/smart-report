"""Color parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RGBA:
    red: float
    green: float
    blue: float
    alpha: float = 1.0

NAMED_COLORS: dict[str, RGBA] = {
    "black": RGBA(0.0, 0.0, 0.0, 1.0),
    "white": RGBA(1.0, 1.0, 1.0, 1.0),
    "red": RGBA(1.0, 0.0, 0.0, 1.0),
    "green": RGBA(0.0, 1.0, 0.0, 1.0),
    "blue": RGBA(0.0, 0.0, 1.0, 1.0),
    "transparent": RGBA(0.0, 0.0, 0.0, 0.0),
}


def parse_color(value: str | RGBA | None) -> RGBA | None:
    if value is None or isinstance(value, RGBA):
        return value

    normalized = value.strip().lower()
    if normalized in NAMED_COLORS:
        return NAMED_COLORS[normalized]

    if normalized.startswith("#"):
        hex_value = normalized[1:]
        if len(hex_value) == 3:
            hex_value = "".join(character * 2 for character in hex_value)
        if len(hex_value) == 6:
            red = int(hex_value[0:2], 16) / 255.0
            green = int(hex_value[2:4], 16) / 255.0
            blue = int(hex_value[4:6], 16) / 255.0
            return RGBA(red, green, blue, 1.0)
        if len(hex_value) == 8:
            red = int(hex_value[0:2], 16) / 255.0
            green = int(hex_value[2:4], 16) / 255.0
            blue = int(hex_value[4:6], 16) / 255.0
            alpha = int(hex_value[6:8], 16) / 255.0
            return RGBA(red, green, blue, alpha)
        raise ValueError(f"Unsupported hex color: {value}")

    if normalized.startswith("rgb(") and normalized.endswith(")"):
        parts = [part.strip() for part in normalized[4:-1].split(",")]
        if len(parts) != 3:
            raise ValueError(f"Unsupported rgb color: {value}")
        red, green, blue = (int(part) / 255.0 for part in parts)
        return RGBA(red, green, blue, 1.0)

    if normalized.startswith("rgba(") and normalized.endswith(")"):
        parts = [part.strip() for part in normalized[5:-1].split(",")]
        if len(parts) != 4:
            raise ValueError(f"Unsupported rgba color: {value}")
        red = int(parts[0]) / 255.0
        green = int(parts[1]) / 255.0
        blue = int(parts[2]) / 255.0
        alpha = float(parts[3])
        return RGBA(red, green, blue, alpha)

    raise ValueError(f"Unsupported color value: {value}")
