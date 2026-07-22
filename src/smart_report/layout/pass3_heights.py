"""Pass 3: resolve heights and local positions."""

from __future__ import annotations

from .node import LayoutNode
from .rich_text_layout import rich_text_height
from .table_model import table_height
from .text_overflow import normalize_text_overflow
from .text_wrap import wrap_text
from ..style.letter_spacing import resolve_letter_spacing
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
        max_flow_extent = _layout_flex_children(node, padding.left, padding.top, content_width, content_height)
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


def _layout_flex_children(
    node: LayoutNode,
    start_x: float,
    start_y: float,
    content_width: float,
    content_height: float | None,
) -> float:
    direction = node.content.get("flex_direction", "row")
    if direction == "column":
        return _layout_flex_column_children(node, start_x, start_y, content_width, content_height)
    if node.content.get("flex_wrap") is True:
        return _layout_flex_row_wrap_children(node, start_x, start_y, content_width)

    flow_children = node.flow_children
    if not flow_children:
        return start_y
    item_count = len(flow_children)
    column_gap = _flex_column_gap(node)
    child_outer_widths = [child.resolved_width + child.style.margin.horizontal for child in flow_children]
    child_outer_heights = [child.resolved_height + child.style.margin.vertical for child in flow_children]
    used_width = sum(child_outer_widths) + column_gap * (item_count - 1)
    remaining_width = max(0.0, content_width - used_width)
    justify = node.content.get("flex_justify", "start")
    justify_offset = 0.0
    gap = column_gap
    if justify == "center":
        justify_offset = remaining_width / 2.0
    elif justify == "end":
        justify_offset = remaining_width
    elif justify == "space-between" and item_count > 1:
        gap += remaining_width / (item_count - 1)

    align = node.content.get("flex_align", "start")
    row_height = max(child_outer_heights)
    cursor_x = 0.0
    for child, child_outer_width, child_outer_height in zip(flow_children, child_outer_widths, child_outer_heights):
        align_offset = 0.0
        if align == "center":
            align_offset = (row_height - child_outer_height) / 2.0
        elif align == "end":
            align_offset = row_height - child_outer_height
        child.local_x = start_x + justify_offset + cursor_x + child.style.margin.left
        child.local_y = start_y + align_offset + child.style.margin.top
        cursor_x += child_outer_width + gap
    return start_y + row_height


def _layout_flex_row_wrap_children(node: LayoutNode, start_x: float, start_y: float, content_width: float) -> float:
    flow_children = node.flow_children
    if not flow_children:
        return start_y

    column_gap = _flex_column_gap(node)
    row_gap = _flex_row_gap(node)
    rows: list[list[tuple[LayoutNode, float, float]]] = []
    current_row: list[tuple[LayoutNode, float, float]] = []
    current_row_width = 0.0

    for child in flow_children:
        child_outer_width = child.resolved_width + child.style.margin.horizontal
        child_outer_height = child.resolved_height + child.style.margin.vertical
        next_row_width = child_outer_width
        if current_row:
            next_row_width = current_row_width + column_gap + child_outer_width

        if current_row and next_row_width > content_width:
            rows.append(current_row)
            current_row = []
            current_row_width = 0.0

        current_row.append((child, child_outer_width, child_outer_height))
        if len(current_row) == 1:
            current_row_width = child_outer_width
        else:
            current_row_width += column_gap + child_outer_width

    if current_row:
        rows.append(current_row)

    justify = node.content.get("flex_justify", "start")
    align = node.content.get("flex_align", "start")
    row_y = start_y
    max_flow_extent = start_y

    for row_index, row in enumerate(rows):
        item_count = len(row)
        row_used_width = sum(child_outer_width for _, child_outer_width, _ in row) + column_gap * (item_count - 1)
        remaining_width = max(0.0, content_width - row_used_width)
        justify_offset = 0.0
        gap = column_gap
        if justify == "center":
            justify_offset = remaining_width / 2.0
        elif justify == "end":
            justify_offset = remaining_width
        elif justify == "space-between" and item_count > 1:
            gap += remaining_width / (item_count - 1)

        row_height = max(child_outer_height for _, _, child_outer_height in row)
        cursor_x = 0.0
        for child, child_outer_width, child_outer_height in row:
            align_offset = 0.0
            if align == "center":
                align_offset = (row_height - child_outer_height) / 2.0
            elif align == "end":
                align_offset = row_height - child_outer_height
            child.local_x = start_x + justify_offset + cursor_x + child.style.margin.left
            child.local_y = row_y + align_offset + child.style.margin.top
            cursor_x += child_outer_width + gap

        max_flow_extent = row_y + row_height
        if row_index < len(rows) - 1:
            row_y += row_height + row_gap

    return max_flow_extent


def _layout_flex_column_children(
    node: LayoutNode,
    start_x: float,
    start_y: float,
    content_width: float,
    content_height: float | None,
) -> float:
    flow_children = node.flow_children
    if not flow_children:
        return start_y

    item_count = len(flow_children)
    row_gap = _flex_row_gap(node)
    child_outer_widths = [child.resolved_width + child.style.margin.horizontal for child in flow_children]
    child_outer_heights = [child.resolved_height + child.style.margin.vertical for child in flow_children]
    used_height = sum(child_outer_heights) + row_gap * (item_count - 1)

    justify_offset = 0.0
    gap = row_gap
    if content_height is not None:
        remaining_height = max(0.0, content_height - used_height)
        justify = node.content.get("flex_justify", "start")
        if justify == "center":
            justify_offset = remaining_height / 2.0
        elif justify == "end":
            justify_offset = remaining_height
        elif justify == "space-between" and item_count > 1:
            gap += remaining_height / (item_count - 1)

    align = node.content.get("flex_align", "start")
    cursor_y = start_y + justify_offset
    max_flow_extent = start_y
    for child, child_outer_width, child_outer_height in zip(flow_children, child_outer_widths, child_outer_heights):
        align_offset = 0.0
        if align == "center":
            align_offset = max(0.0, (content_width - child_outer_width) / 2.0)
        elif align == "end":
            align_offset = max(0.0, content_width - child_outer_width)

        child.local_x = start_x + align_offset + child.style.margin.left
        child.local_y = cursor_y + child.style.margin.top
        cursor_y += child_outer_height + gap
        max_flow_extent = max(max_flow_extent, child.local_y + child.resolved_height + child.style.margin.bottom)
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


def _flex_row_gap(node: LayoutNode) -> float:
    value = node.content.get("row_gap", node.content.get("gap", 0.0))
    return float(value) if isinstance(value, (int, float)) else 0.0


def _flex_column_gap(node: LayoutNode) -> float:
    value = node.content.get("column_gap", node.content.get("gap", 0.0))
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
    if node.node_type == "rect" and "text" in node.content:
        return _measure_text_height(node)
    if node.node_type == "rich_text":
        return rich_text_height(node, node.resolved_width)
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

    if normalize_text_overflow(str(node.content.get("text_overflow", "wrap"))) in {"clip", "ellipsis"}:
        return line_height + node.style.padding.vertical

    wrapped_lines = wrap_text(
        text,
        available_width,
        font_name,
        font_size,
        typography=node.style.typography,
        text_direction=node.style.text_direction,
        letter_spacing=_letter_spacing_points(node),
    )
    return max(line_height, len(wrapped_lines) * line_height) + node.style.padding.vertical


def _letter_spacing_points(node: LayoutNode) -> float:
    return resolve_letter_spacing(node.content.get("letter_spacing"), node.style.font_size)
MAX_LAYOUT_TRACKS = 64
