"""Shared table measurement and style helpers."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from importlib import import_module
from typing import Protocol, cast

from .node import Edges, LayoutNode, clone_layout_node
from .text_wrap import wrap_text
from ..style.color import RGBA, parse_color
from ..style.units import Auto, Fixed, SizeInput, SizeSpec, parse_size, resolve_size


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


@dataclass(frozen=True, slots=True)
class TableCellBox:
    row_index: int
    source_row_index: int
    column_index: int
    x: float
    y: float
    width: float
    height: float
    text: str
    rich_content: LayoutNode | None
    align: str
    background: RGBA | None
    color: RGBA | None
    font_name: str
    font_size: float
    line_height: float
    padding: Edges
    border_color: RGBA | None = None
    border_width: float | None = None
    rowspan: int = 1
    colspan: int = 1


@dataclass(frozen=True, slots=True)
class TableCellSpan:
    row_index: int
    column_index: int
    rowspan: int = 1
    colspan: int = 1


def table_rows(node: LayoutNode) -> list[list[object]]:
    rows = node.content.get("rows")
    if not isinstance(rows, list):
        return []

    normalized_rows: list[list[object]] = []
    for row in cast(list[object], rows):
        if not isinstance(row, list):
            continue
        normalized_rows.append(list(cast(list[object], row)))
    footer_rows = node.content.get("footer_rows")
    if isinstance(footer_rows, list):
        for row in cast(list[object], footer_rows):
            if isinstance(row, list):
                normalized_rows.append(list(cast(list[object], row)))
    return normalized_rows


def table_header_rows(node: LayoutNode) -> int:
    value = node.content.get("header_rows", 1)
    if isinstance(value, int):
        return max(0, value)
    return 1


def table_repeat_header(node: LayoutNode) -> bool:
    value = node.content.get("repeat_header", True)
    return bool(value)


def table_footer_rows(node: LayoutNode) -> int:
    slice_value = node.content.get("slice_footer_rows")
    if isinstance(slice_value, int):
        return max(0, slice_value)
    value = node.content.get("footer_rows")
    if not isinstance(value, list):
        return 0
    return sum(1 for row in cast(list[object], value) if isinstance(row, list))


def table_repeat_footer(node: LayoutNode) -> bool:
    value = node.content.get("repeat_footer", False)
    return bool(value)


def table_cell_padding(node: LayoutNode) -> Edges:
    value = node.content.get("cell_padding")
    if isinstance(value, Edges):
        return value
    return Edges.all(6.0)


def table_header_cell_padding(node: LayoutNode) -> Edges:
    value = node.content.get("header_cell_padding")
    if isinstance(value, Edges):
        return value
    return table_cell_padding(node)


def table_header_background(node: LayoutNode) -> RGBA | None:
    value = node.content.get("header_background")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    return None


def table_header_color(node: LayoutNode) -> RGBA | None:
    value = node.content.get("header_color")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    return node.style.color


def table_zebra_background(node: LayoutNode) -> RGBA | None:
    value = node.content.get("zebra_background")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    return None


def table_header_font_name(node: LayoutNode) -> str:
    value = node.content.get("header_font_name")
    if isinstance(value, str) and value:
        return value
    return node.style.font_name


def table_header_font_size(node: LayoutNode) -> float:
    value = node.content.get("header_font_size")
    if isinstance(value, (int, float)):
        return float(value)
    return node.style.font_size


def table_header_line_height(node: LayoutNode) -> float:
    value = node.content.get("header_line_height")
    if isinstance(value, (int, float)):
        return float(value)
    return node.style.line_height


def table_footer_background(node: LayoutNode) -> RGBA | None:
    value = node.content.get("footer_background")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    return None


def table_footer_color(node: LayoutNode) -> RGBA | None:
    value = node.content.get("footer_color")
    if isinstance(value, RGBA):
        return value
    if isinstance(value, str):
        return parse_color(value)
    return node.style.color


def table_footer_alignments(node: LayoutNode, column_count: int) -> list[str] | None:
    value = node.content.get("footer_align")
    if value is None:
        return None
    return _resolve_alignments(value, column_count)


def table_column_count(rows: Sequence[Sequence[object]]) -> int:
    return max((len(row) for row in rows), default=0)


def table_cell_spans(node: LayoutNode, row_count: int, column_count: int) -> dict[tuple[int, int], TableCellSpan]:
    raw_spans = table_style_map(node, "cell_spans")
    spans: dict[tuple[int, int], TableCellSpan] = {}
    occupied: set[tuple[int, int]] = set()
    for raw_key, raw_value in raw_spans.items():
        row_index, column_index = _parse_cell_key(raw_key)
        if row_index < 0 or column_index < 0 or row_index >= row_count or column_index >= column_count:
            raise ValueError(f"Table span anchor out of range: {raw_key}")
        rowspan, colspan = _parse_span_value(raw_value)
        if row_index + rowspan > row_count or column_index + colspan > column_count:
            raise ValueError(f"Table span extends beyond table bounds: {raw_key}")
        span = TableCellSpan(row_index=row_index, column_index=column_index, rowspan=rowspan, colspan=colspan)
        for occupied_row in range(row_index, row_index + rowspan):
            for occupied_column in range(column_index, column_index + colspan):
                occupied_key = (occupied_row, occupied_column)
                if occupied_key in occupied:
                    raise ValueError(f"Overlapping table spans at row {occupied_row}, column {occupied_column}")
                occupied.add(occupied_key)
        spans[(row_index, column_index)] = span
    return spans


def table_alignments(node: LayoutNode, column_count: int) -> list[str]:
    value = node.content.get("align", "left")
    return _resolve_alignments(value, column_count)


def table_header_alignments(node: LayoutNode, column_count: int) -> list[str] | None:
    value = node.content.get("header_align")
    if value is None:
        return None
    return _resolve_alignments(value, column_count)


def _resolve_alignments(value: object, column_count: int) -> list[str]:
    if isinstance(value, str):
        return [_normalize_align(value)] * column_count
    if isinstance(value, list):
        raw_values = [str(item) for item in value]
        alignments = [_normalize_align(raw_values[index]) if index < len(raw_values) else "left" for index in range(column_count)]
        return alignments
    return ["left"] * column_count


def table_source_row_indices(node: LayoutNode, row_count: int) -> list[int]:
    value = node.content.get("source_row_indices")
    if not isinstance(value, list) or len(value) != row_count:
        return list(range(row_count))
    indices: list[int] = []
    for index, item in enumerate(value):
        indices.append(item if isinstance(item, int) else index)
    return indices


def table_column_widths(node: LayoutNode, total_width: float, column_count: int) -> list[float]:
    if column_count <= 0:
        return []

    raw_widths = node.content.get("column_widths")
    if not isinstance(raw_widths, list):
        return [total_width / column_count] * column_count

    specs: list[SizeSpec] = []
    for index in range(column_count):
        if index < len(raw_widths):
            specs.append(parse_size(cast(SizeInput, raw_widths[index])))
        else:
            specs.append(Auto())

    fixed_total = 0.0
    auto_count = 0
    widths: list[float | None] = []
    for spec in specs:
        if isinstance(spec, Auto):
            auto_count += 1
            widths.append(None)
            continue
        width = resolve_size(spec, total_width, 0.0)
        fixed_total += width
        widths.append(width)

    remaining = max(0.0, total_width - fixed_total)
    if fixed_total > total_width and fixed_total > 0:
        scale = total_width / fixed_total
        return [0.0 if width is None else width * scale for width in widths]

    auto_width = remaining / auto_count if auto_count else 0.0
    return [auto_width if width is None else width for width in widths]


def table_row_heights(node: LayoutNode, rows: Sequence[Sequence[object]], column_widths: list[float]) -> list[float]:
    body_padding = table_cell_padding(node)
    header_padding = table_header_cell_padding(node)
    string_width = _string_width_fn()
    header_rows = table_header_rows(node)
    footer_rows = table_footer_rows(node)
    header_font_name = table_header_font_name(node)
    header_font_size = table_header_font_size(node)
    header_line_height = table_header_line_height(node)
    column_count = len(column_widths)
    spans = table_cell_spans(node, len(rows), column_count)
    covered = _covered_cells(spans)
    heights: list[float] = [24.0] * len(rows)
    pending_rowspans: list[tuple[TableCellSpan, float]] = []
    for row_index, row in enumerate(rows):
        font_name = header_font_name if row_index < header_rows else node.style.font_name
        font_size = header_font_size if row_index < header_rows else node.style.font_size
        line_height = header_line_height if row_index < header_rows else node.style.line_height
        padding = header_padding if row_index < header_rows else body_padding
        for column_index in range(column_count):
            if (row_index, column_index) in covered:
                continue
            cell = row[column_index] if column_index < len(row) else ""
            span = spans.get((row_index, column_index), TableCellSpan(row_index=row_index, column_index=column_index))
            column_width = sum(column_widths[column_index:column_index + span.colspan])
            text_width = max(1.0, column_width - padding.horizontal)
            required_height = _measure_cell_height(cell, text_width, padding, font_name, font_size, line_height, string_width)
            if footer_rows and row_index >= len(rows) - footer_rows:
                required_height = max(required_height, line_height + padding.vertical)
            if span.rowspan == 1:
                heights[row_index] = max(heights[row_index], required_height)
                continue
            pending_rowspans.append((span, required_height))
    for span, required_height in pending_rowspans:
        current_height = sum(heights[span.row_index:span.row_index + span.rowspan])
        if current_height >= required_height:
            continue
        extra_per_row = (required_height - current_height) / span.rowspan
        for row_index in range(span.row_index, span.row_index + span.rowspan):
            heights[row_index] += extra_per_row
    return heights


def table_height(node: LayoutNode) -> float:
    rows = table_rows(node)
    if not rows:
        return 0.0
    widths = table_column_widths(node, node.resolved_width, table_column_count(rows))
    return sum(table_row_heights(node, rows, widths))


def table_cell_boxes(node: LayoutNode, x: float, y: float, width: float, height: float) -> list[TableCellBox]:
    rows = table_rows(node)
    if not rows:
        return []
    column_count = table_column_count(rows)
    spans = table_cell_spans(node, len(rows), column_count)
    covered = _covered_cells(spans)
    source_row_indices = table_source_row_indices(node, len(rows))
    column_widths = table_column_widths(node, width, column_count)
    row_heights = table_row_heights(node, rows, column_widths)
    if row_heights and abs(sum(row_heights) - height) > 0.01:
        scale = height / sum(row_heights) if sum(row_heights) else 1.0
        row_heights = [row_height * scale for row_height in row_heights]

    header_rows = table_header_rows(node)
    footer_rows = table_footer_rows(node)
    header_background = table_header_background(node)
    header_color = table_header_color(node)
    header_alignments = table_header_alignments(node, column_count)
    header_font_name = table_header_font_name(node)
    header_font_size = table_header_font_size(node)
    header_line_height = table_header_line_height(node)
    header_padding = table_header_cell_padding(node)
    footer_background = table_footer_background(node)
    footer_color = table_footer_color(node)
    footer_alignments = table_footer_alignments(node, column_count)
    body_padding = table_cell_padding(node)
    zebra_background = table_zebra_background(node)
    alignments = table_alignments(node, column_count)
    boxes: list[TableCellBox] = []
    cursor_y = y
    for row_index, row in enumerate(rows):
        cursor_x = x
        row_height = row_heights[row_index]
        source_row_index = source_row_indices[row_index]
        for column_index in range(column_count):
            if (row_index, column_index) in covered:
                cursor_x += column_widths[column_index]
                continue
            is_header = row_index < header_rows
            is_footer = footer_rows > 0 and row_index >= len(rows) - footer_rows
            background = header_background if is_header and header_background is not None else node.style.background
            if not is_header and not is_footer and zebra_background is not None and (row_index - header_rows) % 2 == 1:
                background = zebra_background
            if is_footer and footer_background is not None:
                background = footer_background
            color = header_color if is_header else footer_color if is_footer else node.style.color
            font_name = header_font_name if is_header else node.style.font_name
            font_size = header_font_size if is_header else node.style.font_size
            line_height = header_line_height if is_header else node.style.line_height
            padding = header_padding if is_header else body_padding
            column_override = _style_override(table_style_map(node, "column_styles"), column_index)
            row_override = _style_override(table_style_map(node, "row_styles"), source_row_index)
            cell_override = _style_override(table_style_map(node, "cell_styles"), f"{source_row_index}:{column_index}")
            background = _style_color(background, column_override, row_override, cell_override, "background")
            color = _style_color(color, column_override, row_override, cell_override, "color")
            base_align = header_alignments[column_index] if is_header and header_alignments is not None else alignments[column_index]
            if is_footer and footer_alignments is not None:
                base_align = footer_alignments[column_index]
            align = _style_align(base_align, column_override, row_override, cell_override)
            cell = row[column_index] if column_index < len(row) else ""
            rich_content = _cell_rich_content(cell)
            text = "" if rich_content is not None else _cell_text(cell)
            span = spans.get((row_index, column_index), TableCellSpan(row_index=row_index, column_index=column_index))
            cell_width = sum(column_widths[column_index:column_index + span.colspan])
            cell_height = sum(row_heights[row_index:row_index + span.rowspan])
            boxes.append(
                TableCellBox(
                    row_index=row_index,
                    source_row_index=source_row_index,
                    column_index=column_index,
                    x=cursor_x,
                    y=cursor_y,
                    width=cell_width,
                    height=cell_height,
                    text=text,
                    rich_content=rich_content,
                    align=align,
                    background=background,
                    color=color,
                    font_name=font_name,
                    font_size=font_size,
                    line_height=line_height,
                    padding=padding,
                    border_color=_style_border_color(node, column_override, row_override, cell_override),
                    border_width=_style_border_width(node, column_override, row_override, cell_override),
                    rowspan=span.rowspan,
                    colspan=span.colspan,
                )
            )
            cursor_x += column_widths[column_index]
        cursor_y += row_height
    return boxes


def _normalize_align(value: str) -> str:
    lowered = value.lower()
    if lowered in {"left", "center", "right"}:
        return lowered
    raise ValueError(f"Unsupported table alignment: {value}")


def _covered_cells(spans: dict[tuple[int, int], TableCellSpan]) -> set[tuple[int, int]]:
    covered: set[tuple[int, int]] = set()
    for span in spans.values():
        for row_index in range(span.row_index, span.row_index + span.rowspan):
            for column_index in range(span.column_index, span.column_index + span.colspan):
                if row_index == span.row_index and column_index == span.column_index:
                    continue
                covered.add((row_index, column_index))
    return covered


def _parse_cell_key(key: object) -> tuple[int, int]:
    if isinstance(key, str):
        row_text, separator, column_text = key.partition(":")
        if separator:
            return int(row_text), int(column_text)
    if isinstance(key, tuple) and len(key) == 2:
        row_index, column_index = key
        if isinstance(row_index, int) and isinstance(column_index, int):
            return row_index, column_index
    raise ValueError(f"Unsupported table cell key: {key}")


def _parse_span_value(value: object) -> tuple[int, int]:
    if isinstance(value, dict):
        rowspan = value.get("rowspan", 1)
        colspan = value.get("colspan", 1)
    elif isinstance(value, tuple) and len(value) == 2:
        rowspan, colspan = value
    else:
        raise ValueError(f"Unsupported table span value: {value}")
    if not isinstance(rowspan, int) or not isinstance(colspan, int) or rowspan < 1 or colspan < 1:
        raise ValueError("Table span values must be positive integers")
    return rowspan, colspan


def table_span_ranges(node: LayoutNode, row_count: int, column_count: int) -> list[tuple[int, int]]:
    return [(span.row_index, span.row_index + span.rowspan) for span in table_cell_spans(node, row_count, column_count).values() if span.rowspan > 1]


def table_slice_spans(node: LayoutNode, source_row_indices: list[int]) -> dict[str, dict[str, int]]:
    rows = table_rows(node)
    column_count = table_column_count(rows)
    spans = table_cell_spans(node, len(rows), column_count)
    local_by_source = {source_row_index: local_index for local_index, source_row_index in enumerate(source_row_indices)}
    sliced_spans: dict[str, dict[str, int]] = {}
    for span in spans.values():
        span_sources = list(range(span.row_index, span.row_index + span.rowspan))
        if not all(source_row in local_by_source for source_row in span_sources):
            continue
        local_row = local_by_source[span.row_index]
        sliced_spans[f"{local_row}:{span.column_index}"] = {"rowspan": span.rowspan, "colspan": span.colspan}
    return sliced_spans


def layout_rich_cell_content(content: LayoutNode, width: float, x: float, y: float) -> LayoutNode:
    resolve_widths = import_module("smart_report.layout.pass2_widths").resolve_widths
    resolve_heights = import_module("smart_report.layout.pass3_heights").resolve_heights
    rich_node = clone_layout_node(content)
    rich_node.style.width = Fixed(width)
    rich_node.local_x = x
    rich_node.local_y = y
    resolve_widths(rich_node, width)
    resolve_heights(rich_node)
    return rich_node


def _string_width_fn() -> StringWidthFn:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    return cast(StringWidthFn, getattr(pdfmetrics, "stringWidth"))


def table_style_map(node: LayoutNode, key: str) -> dict[object, object]:
    value = node.content.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _style_override(styles: dict[object, object], key: object) -> dict[str, object]:
    value = styles.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _style_color(
    base: RGBA | None,
    column_override: dict[str, object],
    row_override: dict[str, object],
    cell_override: dict[str, object],
    key: str,
) -> RGBA | None:
    for override in (column_override, row_override, cell_override):
        value = override.get(key)
        if isinstance(value, RGBA):
            base = value
    return base


def _style_align(
    base: str,
    column_override: dict[str, object],
    row_override: dict[str, object],
    cell_override: dict[str, object],
) -> str:
    resolved = base
    for override in (column_override, row_override, cell_override):
        value = override.get("align")
        if isinstance(value, str):
            resolved = _normalize_align(value)
    return resolved


def _cell_text(cell: object) -> str:
    if isinstance(cell, LayoutNode):
        return ""
    return str(cell)


def _cell_rich_content(cell: object) -> LayoutNode | None:
    if isinstance(cell, LayoutNode):
        return cell
    return None


def _measure_cell_height(
    cell: object,
    text_width: float,
    padding: Edges,
    font_name: str,
    font_size: float,
    line_height: float,
    string_width: StringWidthFn,
) -> float:
    rich_content = _cell_rich_content(cell)
    if rich_content is not None:
        rich_node = layout_rich_cell_content(rich_content, text_width, 0.0, 0.0)
        return max(24.0, rich_node.resolved_height + padding.vertical)
    lines = wrap_text(_cell_text(cell), text_width, font_name, font_size, string_width)
    return max(24.0, (len(lines) * line_height) + padding.vertical)


def _style_border_color(
    node: LayoutNode,
    column_override: dict[str, object],
    row_override: dict[str, object],
    cell_override: dict[str, object],
) -> RGBA | None:
    base = node.content.get("border_color")
    resolved = base if isinstance(base, RGBA) else node.style.stroke_color or node.style.color
    for override in (column_override, row_override, cell_override):
        value = override.get("border_color")
        if isinstance(value, RGBA):
            resolved = value
    return resolved


def _style_border_width(
    node: LayoutNode,
    column_override: dict[str, object],
    row_override: dict[str, object],
    cell_override: dict[str, object],
) -> float | None:
    _ = node
    resolved: float | None = None
    for override in (column_override, row_override, cell_override):
        value = override.get("border_width")
        if isinstance(value, (int, float)):
            resolved = float(value)
    return resolved
