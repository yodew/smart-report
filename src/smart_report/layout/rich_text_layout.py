"""Rich text layout helpers shared by measurement, rendering, and pagination."""

from __future__ import annotations

from dataclasses import dataclass

from .node import LayoutNode
from .text_wrap import _tokens
from ..style.color import RGBA, parse_color
from ..style.font import DEFAULT_FONT_REGISTRY, shaped_string_width, string_width
from ..style.letter_spacing import resolve_letter_spacing
from ..style.typography import shape_text_for_width


@dataclass(frozen=True, slots=True)
class RichTextFragment:
    text: str
    font_name: str
    font_size: float
    color: RGBA | None
    bold: bool = False
    letter_spacing: float = 0.0


@dataclass(frozen=True, slots=True)
class RichTextLine:
    fragments: tuple[RichTextFragment, ...]
    width: float
    height: float


BASE14_BOLD_FACES = {
    "Helvetica": "Helvetica-Bold",
    "Helvetica-Oblique": "Helvetica-BoldOblique",
    "Times-Roman": "Times-Bold",
    "Times-Italic": "Times-BoldItalic",
    "Courier": "Courier-Bold",
    "Courier-Oblique": "Courier-BoldOblique",
}


def normalize_rich_text_runs(node: LayoutNode) -> list[RichTextFragment | None]:
    """Normalize node runs; ``None`` marks a hard line break."""

    normalized: list[RichTextFragment | None] = []
    runs = node.content.get("runs")
    if not isinstance(runs, list):
        return normalized
    for raw_run in runs:
        if not isinstance(raw_run, dict):
            continue
        if raw_run.get("kind") == "br" or raw_run.get("type") == "br":
            normalized.append(None)
            continue
        text = str(raw_run.get("text", ""))
        if not text:
            continue
        font_size_value = raw_run.get("font_size")
        font_size = float(font_size_value) if isinstance(font_size_value, (int, float)) else node.style.font_size
        bold = bool(raw_run.get("bold", False))
        font_name = _run_font_name(node, raw_run, bold)
        normalized.append(
            RichTextFragment(
                text=text,
                font_name=font_name,
                font_size=font_size,
                color=_run_color(node, raw_run),
                bold=bold,
                letter_spacing=_run_letter_spacing(node, raw_run, font_size),
            )
        )
    return normalized


def rich_text_natural_width(node: LayoutNode) -> float:
    lines = layout_rich_text(node, 1000000.0)
    return max((line.width for line in lines), default=0.0) + node.style.padding.horizontal


def rich_text_height(node: LayoutNode, width: float) -> float:
    lines = layout_rich_text(node, max(1.0, width - node.style.padding.horizontal))
    return max(node.style.line_height, sum(line.height for line in lines)) + node.style.padding.vertical


def split_rich_text_lines(node: LayoutNode, width: float) -> list[RichTextLine]:
    return layout_rich_text(node, max(1.0, width - node.style.padding.horizontal))


def layout_rich_text(node: LayoutNode, width: float) -> list[RichTextLine]:
    fragments = normalize_rich_text_runs(node)
    if not fragments:
        return [_line((), node.style.line_height)]
    lines: list[RichTextLine] = []
    current: list[RichTextFragment] = []
    safe_width = max(1.0, width)

    for fragment in fragments:
        if fragment is None:
            lines.append(_line(tuple(_trim_trailing_space(current)), node.style.line_height))
            current = []
            continue
        for paragraph_index, paragraph in enumerate(fragment.text.split("\n")):
            if paragraph_index > 0:
                lines.append(_line(tuple(_trim_trailing_space(current)), node.style.line_height))
                current = []
            for token in _tokens(paragraph):
                if token.isspace() and not current:
                    continue
                token_fragment = _copy_fragment(fragment, token)
                candidate = current + [token_fragment]
                if _fragments_width(candidate, node) <= safe_width:
                    current = candidate
                    continue
                if current:
                    lines.append(_line(tuple(_trim_trailing_space(current)), node.style.line_height))
                    current = []
                    if token.isspace():
                        continue
                if _fragment_width(token_fragment, node) <= safe_width:
                    current = [token_fragment]
                    continue
                split_parts = _split_long_fragment(token_fragment, safe_width, node)
                lines.extend(_line((part,), node.style.line_height) for part in split_parts[:-1])
                current = [split_parts[-1]] if split_parts else []
    if current or not lines:
        lines.append(_line(tuple(_trim_trailing_space(current)), node.style.line_height))
    return lines


def rich_text_runs_for_lines(lines: list[RichTextLine]) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for line_index, line in enumerate(lines):
        if line_index:
            runs.append({"kind": "br"})
        for fragment in line.fragments:
            run: dict[str, object] = {"kind": "text", "text": fragment.text, "font": fragment.font_name}
            run["font_size"] = fragment.font_size
            if fragment.color is not None:
                run["color"] = [fragment.color.red, fragment.color.green, fragment.color.blue, fragment.color.alpha]
            if fragment.bold:
                run["bold"] = True
            if fragment.letter_spacing != 0:
                run["letter_spacing"] = fragment.letter_spacing
            runs.append(run)
    return runs


def _run_font_name(node: LayoutNode, run: dict[object, object], bold: bool) -> str:
    explicit_font = run.get("font")
    if isinstance(explicit_font, str) and explicit_font:
        return _bold_font_name(explicit_font) if bold else explicit_font
    family = run.get("font_family")
    if isinstance(family, str) and family:
        return DEFAULT_FONT_REGISTRY.font_name_for_family(family, bold=bold)
    if node.style.font_family is not None:
        return DEFAULT_FONT_REGISTRY.font_name_for_family(node.style.font_family, bold=bold)
    return _bold_font_name(node.style.font_name) if bold else node.style.font_name


def _bold_font_name(font_name: str) -> str:
    return BASE14_BOLD_FACES.get(font_name, font_name)


def _run_color(node: LayoutNode, run: dict[object, object]) -> RGBA | None:
    value = run.get("color")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    if isinstance(value, list) and len(value) == 4 and all(isinstance(item, (int, float)) for item in value):
        return RGBA(float(value[0]), float(value[1]), float(value[2]), float(value[3]))
    return node.style.color


def _run_letter_spacing(node: LayoutNode, run: dict[object, object], font_size: float) -> float:
    value = run.get("letter_spacing", node.content.get("letter_spacing"))
    return resolve_letter_spacing(value, font_size)


def _copy_fragment(fragment: RichTextFragment, text: str) -> RichTextFragment:
    return RichTextFragment(text=text, font_name=fragment.font_name, font_size=fragment.font_size, color=fragment.color, bold=fragment.bold, letter_spacing=fragment.letter_spacing)


def _line(fragments: tuple[RichTextFragment, ...], fallback_height: float) -> RichTextLine:
    width = sum(_fragment_width_no_node(fragment) for fragment in fragments)
    height = max(fallback_height, max((fragment.font_size * 1.2 for fragment in fragments), default=fallback_height))
    return RichTextLine(fragments=fragments, width=width, height=height)


def _trim_trailing_space(fragments: list[RichTextFragment]) -> list[RichTextFragment]:
    if fragments and fragments[-1].text.isspace():
        return fragments[:-1]
    if fragments and fragments[-1].text.rstrip() != fragments[-1].text:
        return fragments[:-1] + [_copy_fragment(fragments[-1], fragments[-1].text.rstrip())]
    return fragments


def _fragments_width(fragments: list[RichTextFragment], node: LayoutNode) -> float:
    return sum(_fragment_width(fragment, node) for fragment in _trim_trailing_space(fragments))


def _fragment_width(fragment: RichTextFragment, node: LayoutNode) -> float:
    if node.style.typography == "advanced":
        base_width = shaped_string_width(fragment.text, fragment.font_name, fragment.font_size)
    else:
        base_width = string_width(shape_text_for_width(fragment.text, node.style.typography, node.style.text_direction), fragment.font_name, fragment.font_size)
    return base_width + max(0, len(fragment.text) - 1) * fragment.letter_spacing


def _fragment_width_no_node(fragment: RichTextFragment) -> float:
    return string_width(fragment.text, fragment.font_name, fragment.font_size) + max(0, len(fragment.text) - 1) * fragment.letter_spacing


def _split_long_fragment(fragment: RichTextFragment, width: float, node: LayoutNode) -> list[RichTextFragment]:
    parts: list[RichTextFragment] = []
    current = ""
    for character in fragment.text:
        candidate = f"{current}{character}"
        if current and _fragment_width(_copy_fragment(fragment, candidate), node) > width:
            parts.append(_copy_fragment(fragment, current))
            current = character
            continue
        current = candidate
    if current:
        parts.append(_copy_fragment(fragment, current))
    return parts or [_copy_fragment(fragment, "")]
