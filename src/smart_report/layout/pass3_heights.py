"""Pass 3: resolve heights and local positions."""

from __future__ import annotations

from importlib import import_module
from math import ceil
from typing import Protocol, cast

from .node import LayoutNode
from .table_model import table_height
from ..style.units import Auto, Percent, resolve_size


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


def resolve_heights(root: LayoutNode, available_height: float | None = None) -> None:
    _resolve_node_height(root, available_height)


def _resolve_node_height(node: LayoutNode, available_height: float | None) -> None:
    explicit_height = _resolve_explicit_height(node, available_height)
    child_available_height = None
    if explicit_height is not None:
        child_available_height = max(0.0, explicit_height - node.style.padding.vertical)

    for child in node.children:
        _resolve_node_height(child, child_available_height)

    if node.children:
        _layout_container(node, explicit_height)
        return

    node.resolved_height = _resolve_leaf_height(node, explicit_height)


def _resolve_explicit_height(node: LayoutNode, available_height: float | None) -> float | None:
    if isinstance(node.style.height, Auto):
        return None
    if isinstance(node.style.height, Percent) and available_height is None:
        return None
    return max(0.0, resolve_size(node.style.height, available_height, 0.0))


def _layout_container(node: LayoutNode, explicit_height: float | None) -> None:
    padding = node.style.padding
    content_width = max(0.0, node.resolved_width - padding.horizontal)
    content_height = None
    if explicit_height is not None:
        content_height = max(0.0, explicit_height - padding.vertical)

    cursor_y = padding.top
    max_flow_extent = padding.top
    for child in node.flow_children:
        child.local_x = padding.left + child.style.margin.left
        child.local_y = cursor_y + child.style.margin.top
        cursor_y = (
            child.local_y
            + child.resolved_height
            + child.style.margin.bottom
        )
        max_flow_extent = max(max_flow_extent, cursor_y)

    max_absolute_extent = padding.top
    for child in node.absolute_children:
        child.local_x = padding.left + resolve_size(child.style.left or Auto(), content_width, 0.0)
        child.local_y = padding.top + resolve_size(child.style.top or Auto(), content_height, 0.0)
        max_absolute_extent = max(max_absolute_extent, child.local_y + child.resolved_height)

    if explicit_height is not None:
        node.resolved_height = explicit_height
        return

    node.resolved_height = max(max_flow_extent, max_absolute_extent) + padding.bottom


def _resolve_leaf_height(node: LayoutNode, explicit_height: float | None) -> float:
    if explicit_height is not None:
        return explicit_height

    if node.node_type == "text":
        return _measure_text_height(node)
    if node.node_type == "image":
        intrinsic_height = node.content.get("intrinsic_height")
        if isinstance(intrinsic_height, (int, float)):
            return float(intrinsic_height)
    if node.node_type == "spacer":
        spacer_height = node.content.get("height")
        if isinstance(spacer_height, (int, float)):
            return float(spacer_height)
    if node.node_type == "table":
        return table_height(node)
    if node.node_type == "line":
        return max(node.style.stroke_width, 1.0)

    return 0.0


def _measure_text_height(node: LayoutNode) -> float:
    text = str(node.content.get("text", ""))
    if not text:
        return node.style.line_height

    available_width = max(1.0, node.resolved_width - node.style.padding.horizontal)
    font_name = node.style.font_name
    font_size = node.style.font_size
    line_height = node.style.line_height

    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    string_width = cast(StringWidthFn, getattr(pdfmetrics, "stringWidth"))

    wrapped_lines = 0
    for paragraph in text.splitlines() or [text]:
        if not paragraph.strip():
            wrapped_lines += 1
            continue
        wrapped_lines += _count_wrapped_lines(paragraph, available_width, font_name, font_size, string_width)

    return max(line_height, wrapped_lines * line_height)


def _count_wrapped_lines(
    text: str,
    available_width: float,
    font_name: str,
    font_size: float,
    string_width: StringWidthFn,
) -> int:
    words = text.split()
    if not words:
        return 1

    current_line = ""
    lines = 1
    for word in words:
        candidate = word if not current_line else f"{current_line} {word}"
        candidate_width = float(string_width(candidate, font_name, font_size))
        if candidate_width <= available_width:
            current_line = candidate
            continue

        if current_line:
            lines += 1
            current_line = word
            continue

        single_word_width = float(string_width(word, font_name, font_size))
        lines += max(0, ceil(single_word_width / available_width) - 1)
        current_line = word

    return lines
