"""Pagination helpers for flow-based pages."""

from __future__ import annotations

from math import isfinite

from .node import LayoutNode, clone_layout_node
from ..style.units import Fixed
from .table_model import (
    layout_rich_cell_content,
    table_cell_padding,
    table_cell_spans,
    table_column_count,
    table_column_widths,
    table_header_rows,
    table_footer_rows,
    table_height,
    table_repeat_footer,
    table_repeat_header,
    table_row_heights,
    table_rows,
    table_slice_spans,
    table_span_ranges,
)
from .text_wrap import wrap_text

MAX_FIXED_SPLIT_CHUNKS = 10000
STARTS_ON_FOLLOWING_PAGE = "_starts_on_following_page"


def paginate_page(page: LayoutNode) -> list[LayoutNode]:
    max_page_height = page.resolved_height
    current_page = _clone_page_shell(page)
    paginated_pages: list[LayoutNode] = [current_page]

    for child in page.children:
        if child.style.position.value == "absolute":
            _ = current_page.add_child(clone_layout_node(child))
            continue

        if _flag(child, "page_break_before") and current_page.children:
            current_page = _new_generated_page(page, paginated_pages)

        current_page = _append_with_pagination(
            current_page=current_page,
            source_page=page,
            child=child,
            output_pages=paginated_pages,
            max_page_height=max_page_height,
        )
        if _flag(child, "page_break_after"):
            current_page = _new_generated_page(page, paginated_pages)

    return [page_slice for page_slice in paginated_pages if page_slice.children]


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

    if _flag(child, "keep_together"):
        current_page = _new_generated_page(source_page, output_pages)
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
                if bool(frame_slice.content.pop(STARTS_ON_FOLLOWING_PAGE, False)):
                    current_page = _new_generated_page(source_page, output_pages)
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

    children = frame.children
    for index, child in enumerate(children):
        if child.style.position.value == "absolute":
            _ = current_frame.add_child(clone_layout_node(child))
            continue

        remaining_content_height = max(1.0, current_capacity - current_height)
        if _flag(child, "page_break_before") and current_frame.children:
            current_frame = _clone_frame_shell(frame)
            frame_slices.append(current_frame)
            current_height = 0.0
            current_capacity = following_content_height
            remaining_content_height = current_capacity
        if _flag(child, "keep_with_next") and index + 1 < len(children):
            pair_height = _child_total_height(child) + _child_total_height(children[index + 1])
            if current_frame.children and pair_height > remaining_content_height and pair_height <= following_content_height:
                current_frame = _clone_frame_shell(frame)
                frame_slices.append(current_frame)
                current_height = 0.0
                current_capacity = following_content_height
                remaining_content_height = current_capacity
        split_nodes = _split_flow_child(child, remaining_content_height, following_content_height)
        for split_node in split_nodes:
            child_total_height = split_node.resolved_height + split_node.style.margin.top + split_node.style.margin.bottom
            if current_height + child_total_height > current_capacity and (current_frame.children or child_total_height <= following_content_height):
                starts_on_following_page = not current_frame.children and current_height == 0.0
                current_frame = _clone_frame_shell(frame)
                if starts_on_following_page:
                    current_frame.content[STARTS_ON_FOLLOWING_PAGE] = True
                frame_slices.append(current_frame)
                current_height = 0.0
                current_capacity = following_content_height

            split_node.local_x = frame.style.padding.left + split_node.style.margin.left
            split_node.local_y = current_height + split_node.style.margin.top
            _ = current_frame.add_child(split_node)
            current_height += child_total_height
        if _flag(child, "page_break_after") and current_frame.children:
            current_frame = _clone_frame_shell(frame)
            frame_slices.append(current_frame)
            current_height = 0.0
            current_capacity = following_content_height

    result = [frame_slice for frame_slice in frame_slices if frame_slice.children]
    for frame_slice in result:
        frame_slice.resolved_height = _frame_slice_height(frame_slice)
    return result


def _split_flow_child(child: LayoutNode, first_content_height: float, following_content_height: float) -> list[LayoutNode]:
    child_total_height = child.resolved_height + child.style.margin.top + child.style.margin.bottom
    if child_total_height <= first_content_height:
        return [clone_layout_node(child)]

    if _flag(child, "keep_together") and child_total_height <= following_content_height:
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
    lines = wrap_text(
        text_value,
        text_width,
        child.style.font_name,
        child.style.font_size,
        typography=child.style.typography,
        text_direction=child.style.text_direction,
    )
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
    source_indices = [item if isinstance(item, int) else index for index, item in enumerate(source_row_indices)]

    column_widths = table_column_widths(child, child.resolved_width, table_column_count(rows))
    row_heights = table_row_heights(child, rows, column_widths)
    span_ranges = table_span_ranges(child, len(rows), table_column_count(rows))
    footer_count = min(table_footer_rows(child), len(rows))
    header_count = min(table_header_rows(child), len(rows) - footer_count)
    repeat_header = table_repeat_header(child) and header_count > 0
    repeat_footer = table_repeat_footer(child) and footer_count > 0
    initial_header_height = sum(row_heights[:header_count]) if repeat_header else 0.0
    initial_footer_height = sum(row_heights[len(rows) - footer_count:]) if repeat_footer else 0.0
    rich_row_capacity = max(1.0, min(first_content_height, following_content_height) - initial_header_height - initial_footer_height)
    rows, source_indices = _expand_rich_rows_for_pagination(child, rows, source_indices, column_widths, rich_row_capacity)
    column_widths = table_column_widths(child, child.resolved_width, table_column_count(rows))
    row_heights = table_row_heights(child, rows, column_widths)
    span_ranges = table_span_ranges(child, len(rows), table_column_count(rows))
    footer_count = min(table_footer_rows(child), len(rows))
    header_count = min(table_header_rows(child), len(rows) - footer_count)
    repeat_header = table_repeat_header(child) and header_count > 0
    repeat_footer = table_repeat_footer(child) and footer_count > 0
    header_rows = rows[:header_count]
    header_source_indices = source_indices[:header_count]
    footer_rows = rows[len(rows) - footer_count:] if footer_count else []
    footer_source_indices = source_indices[len(rows) - footer_count:] if footer_count else []
    body_start = header_count if repeat_header else 0
    body_end = len(rows) - footer_count
    body_rows = rows[body_start:body_end]
    body_source_indices = source_indices[body_start:body_end]

    if not body_rows or len(rows) == 1:
        return [clone_layout_node(child)]

    header_height = sum(row_heights[:header_count]) if repeat_header else 0.0
    footer_height = sum(row_heights[len(rows) - footer_count:]) if repeat_footer else 0.0
    slices: list[LayoutNode] = []
    current_rows: list[list[object]] = list(header_rows) if repeat_header else []
    current_source_indices: list[int] = list(header_source_indices) if repeat_header else []
    current_height = header_height + footer_height
    current_capacity = first_content_height
    current_header_rows = header_count if repeat_header else header_count
    minimum_rows_in_slice = len(current_rows) + 1

    for body_index, row in enumerate(body_rows):
        row_offset = body_index + body_start
        row_height = row_heights[row_offset]
        if (
            len(current_rows) >= minimum_rows_in_slice
            and current_height + row_height > current_capacity
            and not _source_rows_have_open_rowspan(source_indices, span_ranges, current_source_indices)
        ):
            slices.append(_clone_table_slice(child, _with_footer_rows(current_rows, footer_rows, repeat_footer), current_source_indices + list(footer_source_indices) if repeat_footer else current_source_indices, current_header_rows, footer_count if repeat_footer else 0))
            current_rows = list(header_rows) if repeat_header else []
            current_source_indices = list(header_source_indices) if repeat_header else []
            current_height = header_height + footer_height
            current_capacity = following_content_height
            current_header_rows = header_count if repeat_header else 0

        current_rows.append(row)
        current_source_indices.append(body_source_indices[body_index])
        current_height += row_height

    if current_rows:
        append_footer = bool(footer_count)
        slices.append(_clone_table_slice(child, _with_footer_rows(current_rows, footer_rows, append_footer), current_source_indices + list(footer_source_indices) if append_footer else current_source_indices, current_header_rows, footer_count if append_footer else 0))

    return slices or [clone_layout_node(child)]


def _expand_rich_rows_for_pagination(
    table: LayoutNode,
    rows: list[list[object]],
    source_indices: list[int],
    column_widths: list[float],
    rich_row_capacity: float,
) -> tuple[list[list[object]], list[int]]:
    column_count = table_column_count(rows)
    spanned_rows = _spanned_row_indices(table, len(rows), column_count)
    footer_count = min(table_footer_rows(table), len(rows))
    header_count = min(table_header_rows(table), len(rows) - footer_count)
    expanded_rows: list[list[object]] = []
    expanded_sources: list[int] = []
    changed = False
    for row_index, row in enumerate(rows):
        is_header = row_index < header_count
        is_footer = footer_count > 0 and row_index >= len(rows) - footer_count
        fragments = [row] if is_header or is_footer or row_index in spanned_rows else _rich_row_fragments(table, row, column_widths, rich_row_capacity)
        if len(fragments) > 1:
            changed = True
        for fragment in fragments:
            expanded_rows.append(fragment)
            expanded_sources.append(source_indices[row_index])
    if not changed:
        return rows, source_indices
    return expanded_rows, expanded_sources


def _spanned_row_indices(table: LayoutNode, row_count: int, column_count: int) -> set[int]:
    rows: set[int] = set()
    for span in table_cell_spans(table, row_count, column_count).values():
        for row_index in range(span.row_index, span.row_index + span.rowspan):
            rows.add(row_index)
    return rows


def _rich_row_fragments(table: LayoutNode, row: list[object], column_widths: list[float], rich_row_capacity: float) -> list[list[object]]:
    rich_cells = [(column_index, cell) for column_index, cell in enumerate(row) if isinstance(cell, LayoutNode)]
    if not rich_cells:
        return [row]
    if len(rich_cells) > 1:
        rich_types = [cell.node_type for _column_index, cell in rich_cells]
        if any(node_type not in {"frame", "text"} for node_type in rich_types) or rich_types.count("frame") > 1:
            return [row]

    padding = table_cell_padding(table)
    content_capacity = max(1.0, rich_row_capacity - padding.vertical)
    rich_fragments_by_column: dict[int, list[LayoutNode]] = {}
    changed = False
    for column_index, rich_cell in rich_cells:
        if column_index >= len(column_widths):
            return [row]
        content_width = max(1.0, column_widths[column_index] - padding.horizontal)
        laid_out = layout_rich_cell_content(rich_cell, content_width, 0.0, 0.0)
        if laid_out.resolved_height <= content_capacity:
            rich_fragments = [laid_out]
        else:
            rich_fragments = _split_rich_cell_node(laid_out, content_capacity)
        if len(rich_fragments) > 1:
            changed = True
        rich_fragments_by_column[column_index] = rich_fragments
    if not changed:
        return [row]

    fragment_count = max(len(fragments) for fragments in rich_fragments_by_column.values())
    rows: list[list[object]] = []
    for fragment_index in range(fragment_count):
        fragment_row = list(row)
        for column_index, rich_fragments in rich_fragments_by_column.items():
            fragment_row[column_index] = rich_fragments[fragment_index] if fragment_index < len(rich_fragments) else ""
        if fragment_index > 0:
            for cell_index, cell in enumerate(fragment_row):
                if cell_index not in rich_fragments_by_column and not isinstance(cell, LayoutNode):
                    fragment_row[cell_index] = ""
        rows.append(fragment_row)
    return rows


def _split_rich_cell_node(rich_cell: LayoutNode, content_capacity: float) -> list[LayoutNode]:
    if rich_cell.node_type == "frame":
        return split_frame_node(rich_cell, content_capacity, content_capacity)
    if rich_cell.node_type == "text":
        return _split_text_node(rich_cell, content_capacity, content_capacity)
    return [clone_layout_node(rich_cell)]


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


def _clone_table_slice(child: LayoutNode, rows: list[list[object]], source_row_indices: list[int], header_rows: int, footer_rows: int = 0) -> LayoutNode:
    node = clone_layout_node(child, include_children=False)
    node.content["rows"] = rows
    node.content["footer_rows"] = []
    node.content["source_row_indices"] = source_row_indices
    node.content["header_rows"] = header_rows
    node.content["slice_footer_rows"] = footer_rows
    node.content["cell_spans"] = table_slice_spans(child, source_row_indices)
    node.resolved_height = table_height(node)
    return node


def _with_footer_rows(rows: list[list[object]], footer_rows: list[list[object]], repeat_footer: bool) -> list[list[object]]:
    if not repeat_footer:
        return rows
    return rows + list(footer_rows)


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


def _flag(node: LayoutNode, key: str) -> bool:
    return bool(node.content.get(key, False))


def _child_total_height(child: LayoutNode) -> float:
    return child.resolved_height + child.style.margin.top + child.style.margin.bottom
