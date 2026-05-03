"""Pagination helpers for flow-based pages."""

from __future__ import annotations

from math import isfinite

from .node import LayoutNode, clone_layout_node
from ..style.units import Fixed
from .table_model import (
    table_column_count,
    table_column_widths,
    table_header_rows,
    table_height,
    table_repeat_header,
    table_row_heights,
    table_rows,
    table_slice_spans,
    table_span_ranges,
)
from .text_wrap import wrap_text

MAX_FIXED_SPLIT_CHUNKS = 10000


def paginate_page(page: LayoutNode) -> list[LayoutNode]:
    max_page_height = page.resolved_height
    current_page = _clone_page_shell(page)
    paginated_pages: list[LayoutNode] = [current_page]

    for child in page.children:
        if child.style.position.value == "absolute":
            _ = current_page.add_child(clone_layout_node(child))
            continue

        current_page = _append_with_pagination(
            current_page=current_page,
            source_page=page,
            child=child,
            output_pages=paginated_pages,
            max_page_height=max_page_height,
        )

    return paginated_pages


def _append_with_pagination(
    current_page: LayoutNode,
    source_page: LayoutNode,
    child: LayoutNode,
    output_pages: list[LayoutNode],
    max_page_height: float,
) -> LayoutNode:
    content_bottom = max(1.0, max_page_height - current_page.style.padding.bottom)
    if child.local_y + child.resolved_height <= content_bottom:
        _ = current_page.add_child(clone_layout_node(child))
        return current_page

    if child.node_type == "frame":
        remaining_height = max(1.0, content_bottom - _current_page_flow_extent(current_page))
        frame_slices = split_frame_node(child, remaining_height, max_page_height)
        if not frame_slices:
            _ = current_page.add_child(clone_layout_node(child))
            return current_page

        first_slice = True
        for frame_slice in frame_slices:
            if first_slice:
                _ = current_page.add_child(frame_slice)
                first_slice = False
                continue
            current_page = _new_generated_page(source_page, output_pages)
            _ = current_page.add_child(frame_slice)
        return current_page

    current_page = _new_generated_page(source_page, output_pages)
    _ = current_page.add_child(clone_layout_node(child))
    return current_page


def split_frame_node(frame: LayoutNode, first_page_height: float, following_page_height: float) -> list[LayoutNode]:
    first_available_height = max(1.0, first_page_height - frame.style.margin.top - frame.style.margin.bottom)
    following_available_height = max(1.0, following_page_height - frame.style.margin.top - frame.style.margin.bottom)
    first_content_height = max(1.0, first_available_height - frame.style.padding.vertical)
    following_content_height = max(1.0, following_available_height - frame.style.padding.vertical)

    current_frame = _clone_frame_shell(frame)
    current_height = 0.0
    frame_slices: list[LayoutNode] = [current_frame]
    current_capacity = first_content_height

    for child in frame.children:
        if child.style.position.value == "absolute":
            _ = current_frame.add_child(clone_layout_node(child))
            continue

        remaining_content_height = max(1.0, current_capacity - current_height)
        split_nodes = _split_flow_child(child, remaining_content_height, following_content_height)
        for split_node in split_nodes:
            child_total_height = split_node.resolved_height + split_node.style.margin.top + split_node.style.margin.bottom
            if current_frame.children and current_height + child_total_height > current_capacity:
                current_frame = _clone_frame_shell(frame)
                frame_slices.append(current_frame)
                current_height = 0.0
                current_capacity = following_content_height

            split_node.local_x = frame.style.padding.left + split_node.style.margin.left
            split_node.local_y = current_height + split_node.style.margin.top
            _ = current_frame.add_child(split_node)
            current_height += child_total_height

    result = [frame_slice for frame_slice in frame_slices if frame_slice.children]
    for frame_slice in result:
        frame_slice.resolved_height = _frame_slice_height(frame_slice)
    return result


def _split_flow_child(child: LayoutNode, first_content_height: float, following_content_height: float) -> list[LayoutNode]:
    child_total_height = child.resolved_height + child.style.margin.top + child.style.margin.bottom
    if child_total_height <= first_content_height:
        return [clone_layout_node(child)]

    first_node_height = max(1.0, first_content_height - child.style.margin.top - child.style.margin.bottom)
    following_node_height = max(1.0, following_content_height - child.style.margin.top - child.style.margin.bottom)

    if child.node_type == "text":
        return _split_text_node(child, first_node_height, following_node_height)
    if child.node_type == "table":
        return _split_table_node(child, first_node_height, following_node_height)
    if child.node_type == "frame":
        return split_frame_node(child, first_node_height, following_node_height) or [clone_layout_node(child)]
    if child.node_type in {"spacer", "rect"}:
        return _split_fixed_height_node(child, first_node_height, following_node_height)

    return [clone_layout_node(child)]


def _split_text_node(child: LayoutNode, first_content_height: float, following_content_height: float) -> list[LayoutNode]:
    text_value = str(child.content.get("text", ""))
    if not text_value:
        return [clone_layout_node(child)]

    text_width = max(1.0, child.resolved_width - child.style.padding.horizontal)
    lines = wrap_text(text_value, text_width, child.style.font_name, child.style.font_size)
    result: list[LayoutNode] = []
    start = 0
    max_lines = _max_text_lines(first_content_height - child.style.padding.vertical, child.style.line_height)
    while start < len(lines):
        end = min(len(lines), start + max_lines)
        chunk_lines = lines[start:end]
        chunk = "\n".join(chunk_lines)
        node = clone_layout_node(child, include_children=False)
        node.content["text"] = chunk
        node.resolved_height = max(child.style.line_height, len(chunk_lines) * child.style.line_height) + child.style.padding.vertical
        result.append(node)
        start = end
        max_lines = _max_text_lines(following_content_height - child.style.padding.vertical, child.style.line_height)
    return result or [clone_layout_node(child)]


def _split_table_node(child: LayoutNode, first_content_height: float, following_content_height: float) -> list[LayoutNode]:
    rows = table_rows(child)
    if not rows:
        return [clone_layout_node(child)]

    source_row_indices = child.content.get("source_row_indices")
    if not isinstance(source_row_indices, list) or len(source_row_indices) != len(rows):
        source_row_indices = list(range(len(rows)))

    column_widths = table_column_widths(child, child.resolved_width, table_column_count(rows))
    row_heights = table_row_heights(child, rows, column_widths)
    span_ranges = table_span_ranges(child, len(rows), table_column_count(rows))
    header_count = min(table_header_rows(child), len(rows))
    repeat_header = table_repeat_header(child) and header_count > 0
    header_rows = rows[:header_count]
    header_source_indices = source_row_indices[:header_count]
    body_start = header_count if repeat_header else 0
    body_rows = rows[body_start:]
    body_source_indices = source_row_indices[body_start:]

    if not body_rows or len(rows) == 1:
        return [clone_layout_node(child)]

    header_height = sum(row_heights[:header_count]) if repeat_header else 0.0
    slices: list[LayoutNode] = []
    current_rows: list[list[str]] = list(header_rows) if repeat_header else []
    current_source_indices: list[int] = list(header_source_indices) if repeat_header else []
    current_height = header_height
    current_capacity = first_content_height
    current_header_rows = header_count if repeat_header else header_count
    minimum_rows_in_slice = len(current_rows) + 1

    for body_index, row in enumerate(body_rows):
        row_offset = body_index + body_start
        row_height = row_heights[row_offset]
        if (
            len(current_rows) >= minimum_rows_in_slice
            and current_height + row_height > current_capacity
            and not _source_rows_have_open_rowspan(source_row_indices, span_ranges, current_source_indices)
        ):
            slices.append(_clone_table_slice(child, current_rows, current_source_indices, current_header_rows))
            current_rows = list(header_rows) if repeat_header else []
            current_source_indices = list(header_source_indices) if repeat_header else []
            current_height = header_height
            current_capacity = following_content_height
            current_header_rows = header_count if repeat_header else 0

        current_rows.append(row)
        current_source_indices.append(body_source_indices[body_index])
        current_height += row_height

    if current_rows:
        slices.append(_clone_table_slice(child, current_rows, current_source_indices, current_header_rows))

    return slices or [clone_layout_node(child)]


def _max_text_lines(content_height: float, line_height: float) -> int:
    return max(1, int(content_height // max(1.0, line_height)))


def _split_fixed_height_node(child: LayoutNode, first_content_height: float, following_content_height: float) -> list[LayoutNode]:
    if child.resolved_height <= 0:
        return [clone_layout_node(child)]
    if not isfinite(child.resolved_height):
        raise ValueError("Fixed-height pagination requires finite heights")

    result: list[LayoutNode] = []
    remaining_height = child.resolved_height
    capacity = max(1.0, first_content_height)
    while remaining_height > 0:
        if len(result) >= MAX_FIXED_SPLIT_CHUNKS:
            raise ValueError("Fixed-height pagination produced too many fragments")
        chunk_height = min(remaining_height, capacity)
        node = clone_layout_node(child, include_children=False)
        node.resolved_height = chunk_height
        node.style.height = Fixed(chunk_height)
        if node.node_type == "spacer":
            node.content["height"] = chunk_height
        result.append(node)
        remaining_height -= chunk_height
        capacity = max(1.0, following_content_height)
    return result or [clone_layout_node(child)]


def _frame_slice_height(frame: LayoutNode) -> float:
    if not frame.children:
        return frame.style.padding.vertical
    flow_extent = max(
        (
            child.local_y
            + child.resolved_height
            + child.style.margin.bottom
            for child in frame.flow_children
        ),
        default=frame.style.padding.top,
    )
    absolute_extent = max(
        (
            child.local_y + child.resolved_height
            for child in frame.absolute_children
        ),
        default=frame.style.padding.top,
    )
    return max(flow_extent, absolute_extent) + frame.style.padding.bottom


def _clone_table_slice(child: LayoutNode, rows: list[list[str]], source_row_indices: list[int], header_rows: int) -> LayoutNode:
    node = clone_layout_node(child, include_children=False)
    node.content["rows"] = rows
    node.content["source_row_indices"] = source_row_indices
    node.content["header_rows"] = header_rows
    node.content["cell_spans"] = table_slice_spans(child, source_row_indices)
    node.resolved_height = table_height(node)
    return node


def _source_rows_have_open_rowspan(
    all_source_row_indices: list[int],
    span_ranges: list[tuple[int, int]],
    candidate_source_indices: list[int],
) -> bool:
    candidate_sources = set(candidate_source_indices)
    for start, end in span_ranges:
        span_sources = set(all_source_row_indices[start:end])
        if candidate_sources.intersection(span_sources) and not span_sources.issubset(candidate_sources):
            return True
    return False


def _current_page_flow_extent(page: LayoutNode) -> float:
    if not page.children:
        return page.style.padding.top
    return max(
        (
            child.local_y
            + child.resolved_height
            + child.style.margin.bottom
            for child in page.children
            if child.style.position.value == "flow"
        ),
        default=page.style.padding.top,
    )


def _clone_page_shell(page: LayoutNode) -> LayoutNode:
    clone = clone_layout_node(page, include_children=False)
    clone.children = []
    return clone


def _clone_frame_shell(frame: LayoutNode) -> LayoutNode:
    clone = clone_layout_node(frame, include_children=False)
    clone.children = []
    return clone


def _new_generated_page(source_page: LayoutNode, output_pages: list[LayoutNode]) -> LayoutNode:
    new_page = _clone_page_shell(source_page)
    output_pages.append(new_page)
    return new_page
