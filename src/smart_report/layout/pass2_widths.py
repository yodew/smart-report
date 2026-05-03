"""Pass 2: resolve widths top-down."""

from __future__ import annotations

from .node import LayoutNode
from ..style.units import Percent
from ..style.units import resolve_size


def resolve_widths(root: LayoutNode, available_width: float | None = None) -> None:
    """Resolve all node widths using a top-down traversal.

    The parent content box is the reference for child percentage widths.
    """

    root_width = available_width if available_width is not None else root.resolved_width
    _resolve_node_width(root, root_width)


def _resolve_node_width(node: LayoutNode, available_width: float) -> None:
    width_reference = available_width
    auto_width = available_width
    if node.style.position.value == "flow":
        flow_width = max(0.0, available_width - node.style.margin.horizontal)
        auto_width = flow_width
        if isinstance(node.style.width, Percent):
            width_reference = flow_width

    node.resolved_width = max(0.0, resolve_size(node.style.width, width_reference, auto_width))

    child_reference_width = max(0.0, node.resolved_width - node.style.padding.horizontal)
    child_widths = _child_available_widths(node, child_reference_width)
    for child, child_available_width in zip(node.children, child_widths):
        _resolve_node_width(child, child_available_width)


def _child_available_widths(node: LayoutNode, content_width: float) -> list[float]:
    children = node.children
    if not children:
        return []

    layout = node.content.get("layout", "flow")
    gap = _layout_gap(node)
    if layout == "grid":
        columns = _bounded_int(node.content.get("grid_columns"), 1, MAX_LAYOUT_TRACKS)
        track_width = max(0.0, (content_width - (gap * (columns - 1))) / columns)
        return [track_width] * len(children)
    if layout == "columns":
        columns = _bounded_int(node.content.get("column_count"), 1, MAX_LAYOUT_TRACKS)
        column_width = max(0.0, (content_width - (gap * (columns - 1))) / columns)
        return [column_width] * len(children)
    if layout == "flex" and node.content.get("flex_direction", "row") == "row":
        flow_children = [child for child in children if child.style.position.value == "flow"]
        item_count = max(1, len(flow_children))
        item_width = max(0.0, (content_width - (gap * (item_count - 1))) / item_count)
        return [item_width if child.style.position.value == "flow" else content_width for child in children]
    return [content_width] * len(children)


def _layout_gap(node: LayoutNode) -> float:
    value = node.content.get("gap", 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _bounded_int(value: object, default: int, maximum: int) -> int:
    if isinstance(value, int) and 1 <= value <= maximum:
        return value
    return default
MAX_LAYOUT_TRACKS = 64
