"""Pass 3: resolve heights and local positions."""

from __future__ import annotations

from .node import LayoutNode
from .table_model import table_height
from .text_wrap import wrap_text
from ..style.units import Auto, Percent, resolve_size


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

    layout = node.content.get("layout", "flow")
    if layout == "grid":
        max_flow_extent = _layout_grid_children(node, padding.left, padding.top, content_width)
    elif layout == "columns":
        max_flow_extent = _layout_column_children(node, padding.left, padding.top, content_width)
    elif layout == "flex":
        max_flow_extent = _layout_flex_children(node, padding.left, padding.top)
    else:
        max_flow_extent = _layout_flow_children(node, padding.left, padding.top)

    if explicit_height is None:
        content_height = _auto_content_height_for_absolute_children(node, max_flow_extent - padding.top)

    max_absolute_extent = padding.top
    for child in node.absolute_children:
        child.local_x = padding.left + resolve_size(child.style.left or Auto(), content_width, 0.0)
        child.local_y = padding.top + resolve_size(child.style.top or Auto(), content_height, 0.0)
        max_absolute_extent = max(max_absolute_extent, child.local_y + child.resolved_height)

    if explicit_height is not None:
        node.resolved_height = explicit_height
        return

    node.resolved_height = max(max_flow_extent, max_absolute_extent) + padding.bottom


def _auto_content_height_for_absolute_children(node: LayoutNode, flow_content_height: float) -> float:
    content_height = max(0.0, flow_content_height)
    for child in node.absolute_children:
        top = child.style.top or Auto()
        if isinstance(top, Percent):
            if top.ratio >= 1.0:
                raise ValueError("Percentage absolute top must be less than 100% when parent height is auto")
            if top.ratio < 1.0:
                content_height = max(content_height, child.resolved_height / max(0.000001, 1.0 - top.ratio))
            continue
        top_offset = resolve_size(top, None, 0.0)
        content_height = max(content_height, top_offset + child.resolved_height)
    return content_height


def _layout_flow_children(node: LayoutNode, start_x: float, start_y: float) -> float:
    cursor_y = start_y
    max_flow_extent = start_y
    for child in node.flow_children:
        child.local_x = start_x + child.style.margin.left
        child.local_y = cursor_y + child.style.margin.top
        cursor_y = child.local_y + child.resolved_height + child.style.margin.bottom
        max_flow_extent = max(max_flow_extent, cursor_y)
    return max_flow_extent


def _layout_flex_children(node: LayoutNode, start_x: float, start_y: float) -> float:
    direction = node.content.get("flex_direction", "row")
    if direction == "column":
        return _layout_flex_column_children(node, start_x, start_y)

    flow_children = node.flow_children
    if not flow_children:
        return start_y
    gap = _layout_gap(node)
    cursor_x = start_x
    max_bottom = start_y
    for child in flow_children:
        child.local_x = cursor_x + child.style.margin.left
        child.local_y = start_y + child.style.margin.top
        cursor_x += child.resolved_width + child.style.margin.horizontal + gap
        max_bottom = max(max_bottom, child.local_y + child.resolved_height + child.style.margin.bottom)
    return max_bottom


def _layout_flex_column_children(node: LayoutNode, start_x: float, start_y: float) -> float:
    flow_children = node.flow_children
    if not flow_children:
        return start_y
    gap = _layout_gap(node)
    cursor_y = start_y
    max_flow_extent = start_y
    for index, child in enumerate(flow_children):
        if index > 0:
            cursor_y += gap
        child.local_x = start_x + child.style.margin.left
        child.local_y = cursor_y + child.style.margin.top
        cursor_y = child.local_y + child.resolved_height + child.style.margin.bottom
        max_flow_extent = max(max_flow_extent, cursor_y)
    return max_flow_extent


def _layout_grid_children(node: LayoutNode, start_x: float, start_y: float, content_width: float) -> float:
    flow_children = node.flow_children
    if not flow_children:
        return start_y
    columns = _bounded_int(node.content.get("grid_columns"), 1, MAX_LAYOUT_TRACKS)
    gap = _layout_gap(node)
    track_width = max(0.0, (content_width - (gap * (columns - 1))) / columns)
    max_flow_extent = start_y
    row_y = start_y
    for row_start in range(0, len(flow_children), columns):
        row_children = flow_children[row_start:row_start + columns]
        row_height = max((child.resolved_height + child.style.margin.vertical for child in row_children), default=0.0)
        for column_index, child in enumerate(row_children):
            child.local_x = start_x + (column_index * (track_width + gap)) + child.style.margin.left
            child.local_y = row_y + child.style.margin.top
        row_y += row_height + gap
        max_flow_extent = max(max_flow_extent, row_y - gap)
    return max_flow_extent


def _layout_column_children(node: LayoutNode, start_x: float, start_y: float, content_width: float) -> float:
    flow_children = node.flow_children
    if not flow_children:
        return start_y
    column_count = _bounded_int(node.content.get("column_count"), 1, MAX_LAYOUT_TRACKS)
    gap = _layout_gap(node)
    column_width = max(0.0, (content_width - (gap * (column_count - 1))) / column_count)
    column_heights = [0.0] * column_count
    for child in flow_children:
        column_index = min(range(column_count), key=lambda index: column_heights[index])
        child.local_x = start_x + (column_index * (column_width + gap)) + child.style.margin.left
        child.local_y = start_y + column_heights[column_index] + child.style.margin.top
        column_heights[column_index] += child.style.margin.top + child.resolved_height + child.style.margin.bottom + gap
    return start_y + max((height - gap for height in column_heights), default=0.0)


def _layout_gap(node: LayoutNode) -> float:
    value = node.content.get("gap", 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _bounded_int(value: object, default: int, maximum: int) -> int:
    if isinstance(value, int) and 1 <= value <= maximum:
        return value
    return default


def _resolve_leaf_height(node: LayoutNode, explicit_height: float | None) -> float:
    if explicit_height is not None:
        return explicit_height

    if node.node_type == "text":
        return _measure_text_height(node)
    if node.node_type == "image":
        intrinsic_width = node.content.get("intrinsic_width")
        intrinsic_height = node.content.get("intrinsic_height")
        if isinstance(intrinsic_width, (int, float)) and isinstance(intrinsic_height, (int, float)) and intrinsic_width > 0:
            return max(0.0, (node.resolved_width / float(intrinsic_width)) * float(intrinsic_height))
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
        return node.style.line_height + node.style.padding.vertical

    available_width = max(1.0, node.resolved_width - node.style.padding.horizontal)
    font_name = node.style.font_name
    font_size = node.style.font_size
    line_height = node.style.line_height

    wrapped_lines = wrap_text(
        text,
        available_width,
        font_name,
        font_size,
        typography=node.style.typography,
        text_direction=node.style.text_direction,
    )
    return max(line_height, len(wrapped_lines) * line_height) + node.style.padding.vertical
MAX_LAYOUT_TRACKS = 64
