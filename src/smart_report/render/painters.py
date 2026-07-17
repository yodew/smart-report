"""Painter registry for render items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from ..layout.node import Rect, RenderItem
from ..layout.pass4_render import build_render_list
from ..layout.rich_text_layout import layout_rich_text
from ..layout.table_model import TableCellBox, layout_rich_cell_content, table_cell_boxes
from ..layout.text_overflow import fit_plain_overflow_text, normalize_plain_overflow_text, normalize_text_overflow
from ..layout.text_wrap import text_width, wrap_text
from ..style.color import RGBA
from ..style.font import string_width
from ..style.letter_spacing import resolve_letter_spacing
from ..style.typography import shape_text
from .rl_adapter import ReportLabCanvasAdapter

Painter = Callable[[ReportLabCanvasAdapter, RenderItem], None]
Orientation = Literal["horizontal", "vertical"]


@dataclass(frozen=True, slots=True)
class _BorderCandidate:
    color: RGBA | None
    width: float
    row_index: int
    column_index: int


def paint_render_item(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    with adapter.isolated_state():
        for clip_rect in item.clip_rects:
            adapter.apply_clip_rect(clip_rect)

        painter = PAINTERS.get(item.node.node_type)
        if painter is None:
            return
        painter(adapter, item)


def paint_text(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    bounds = item.absolute_bounds
    padding = node.style.padding
    text_value = str(node.content.get("text", ""))
    text_value = text_value.replace("{page_number}", str(node.page_index + 1))
    total_pages = node.content.get("total_pages")
    if isinstance(total_pages, int):
        text_value = text_value.replace("{total_pages}", str(total_pages))
    section_name = node.content.get("section_name")
    text_value = text_value.replace("{section_name}", section_name if isinstance(section_name, str) else "")
    section_page_number = node.content.get("section_page_number")
    if isinstance(section_page_number, int):
        text_value = text_value.replace("{section_page_number}", str(section_page_number))
    section_total_pages = node.content.get("section_total_pages")
    if isinstance(section_total_pages, int):
        text_value = text_value.replace("{section_total_pages}", str(section_total_pages))
    content_width = max(1.0, bounds.width - padding.horizontal)
    text_overflow = normalize_text_overflow(str(node.content.get("text_overflow", "wrap")))
    letter_spacing = _letter_spacing_points(node)
    rendered_text = _text_paint_text(node, text_value, content_width, text_overflow, letter_spacing)
    content_rect = Rect(
        x=bounds.x + padding.left,
        y=bounds.y + padding.top,
        width=content_width,
        height=max(0.0, bounds.height - padding.vertical),
    )
    with adapter.isolated_state():
        if text_overflow in {"clip", "ellipsis"}:
            adapter.apply_clip_rect(content_rect)
        adapter.draw_text(
            x=content_rect.x,
            y=content_rect.y,
            width=content_rect.width,
            text=rendered_text,
            font_name=node.style.font_name,
            font_size=node.style.font_size,
            line_height=node.style.line_height,
            typography=node.style.typography,
            text_direction=node.style.text_direction,
            color=node.style.color,
            align=str(node.content.get("align", "left")),
            height=content_rect.height,
            valign=str(node.content.get("valign", "top")),
            letter_spacing=letter_spacing,
            text_overflow=text_overflow,
        )
    link_url = node.content.get("link_url")
    if isinstance(link_url, str):
        _paint_text_link_annotations(adapter, item, rendered_text, link_url, text_overflow)


def paint_rich_text(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    bounds = item.absolute_bounds
    padding = node.style.padding
    content_width = max(1.0, bounds.width - padding.horizontal)
    lines = layout_rich_text(node, content_width)
    adapter.draw_rich_text(
        x=bounds.x + padding.left,
        y=bounds.y + padding.top,
        width=content_width,
        lines=lines,
        align=str(node.content.get("align", "left")),
        height=max(0.0, bounds.height - padding.vertical),
        valign=str(node.content.get("valign", "top")),
    )


def _paint_text_link_annotations(adapter: ReportLabCanvasAdapter, item: RenderItem, text_value: str, link_url: str, text_overflow: str = "wrap") -> None:
    node = item.node
    bounds = item.absolute_bounds
    padding = node.style.padding
    content_x = bounds.x + padding.left
    content_y = bounds.y + padding.top
    content_width = max(1.0, bounds.width - padding.horizontal)
    letter_spacing = _letter_spacing_points(node)
    if text_overflow in {"clip", "ellipsis"}:
        wrapped_lines = [text_value]
    else:
        wrapped_lines = wrap_text(
            text_value,
            content_width,
            node.style.font_name,
            node.style.font_size,
            typography=node.style.typography,
            text_direction=node.style.text_direction,
            letter_spacing=letter_spacing,
        )
    text_height = max(node.style.line_height, len(wrapped_lines) * node.style.line_height)
    content_height = max(0.0, bounds.height - padding.vertical)
    vertical_offset = 0.0
    valign = node.content.get("valign", "top")
    if valign == "middle":
        vertical_offset = max(0.0, content_height - text_height) / 2.0
    elif valign == "bottom":
        vertical_offset = max(0.0, content_height - text_height)
    for line_index, line in enumerate(wrapped_lines):
        display_line = shape_text(line, node.style.typography, node.style.text_direction)
        line_width = min(content_width, text_width(display_line, node.style.font_name, node.style.font_size, string_width, node.style.typography, node.style.text_direction, letter_spacing))
        if line_width <= 0:
            continue
        offset = max(0.0, content_width - line_width)
        if node.content.get("align") == "center":
            offset /= 2
        elif node.content.get("align") == "left" and node.style.text_direction != "rtl":
            offset = 0.0
        elif node.content.get("align") is None and node.style.text_direction != "rtl":
            offset = 0.0
        adapter.link_url(
            link_url,
            Rect(
                x=content_x + offset,
                y=content_y + vertical_offset + (line_index * node.style.line_height),
                width=line_width,
                height=node.style.line_height,
            ),
        )


def _text_paint_text(node: object, text: str, width: float, text_overflow: str, letter_spacing: float) -> str:
    style = getattr(node, "style")
    if text_overflow == "clip":
        return normalize_plain_overflow_text(text)
    if text_overflow == "ellipsis":
        return fit_plain_overflow_text(
            text,
            width,
            style.font_name,
            style.font_size,
            style.typography,
            style.text_direction,
            letter_spacing,
            string_width,
        )
    return text


def _letter_spacing_points(node: object) -> float:
    content = getattr(node, "content", {})
    style = getattr(node, "style", None)
    font_size = float(getattr(style, "font_size", 12.0))
    value = content.get("letter_spacing") if isinstance(content, dict) else None
    return resolve_letter_spacing(value, font_size)


def paint_image(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    image_source = item.node.content.get("src_bytes") or item.node.content.get("src")
    if not isinstance(image_source, (str, bytes)):
        return
    fit = item.node.content.get("object_fit", "stretch")
    object_fit = fit if isinstance(fit, str) else "stretch"
    radius = item.node.style.border_radius
    if not radius.is_zero:
        with adapter.isolated_state():
            adapter.apply_clip_rounded_rect(item.absolute_bounds, radius)
            adapter.draw_image(image_source, item.absolute_bounds, opacity=item.node.style.opacity, fit=object_fit)
        return
    adapter.draw_image(image_source, item.absolute_bounds, opacity=item.node.style.opacity, fit=object_fit)


def paint_rect(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    adapter.draw_rect(
        rect=item.absolute_bounds,
        fill=node.style.background,
        stroke=node.style.stroke_color,
        stroke_width=node.style.stroke_width,
        radius=node.style.border_radius,
    )


def paint_line(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    start_x = item.absolute_bounds.x
    start_y = item.absolute_bounds.y
    end_x = start_x + item.absolute_bounds.width
    end_y = start_y + item.absolute_bounds.height
    adapter.draw_line(start_x, start_y, end_x, end_y, node.style.stroke_color, node.style.stroke_width)


def paint_canvas_background(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    if node.style.background is None and node.style.stroke_color is None:
        return
    adapter.draw_rect(
        rect=item.absolute_bounds,
        fill=node.style.background,
        stroke=node.style.stroke_color,
        stroke_width=node.style.stroke_width,
        radius=node.style.border_radius,
    )


def paint_table(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    node = item.node
    bounds = item.absolute_bounds
    cell_boxes = table_cell_boxes(node, bounds.x, bounds.y, bounds.width, bounds.height)
    if not cell_boxes:
        return

    radius = node.style.border_radius
    if not radius.is_zero:
        with adapter.isolated_state():
            adapter.apply_clip_rounded_rect(bounds, radius)
            _paint_table_cells(adapter, item, cell_boxes)
        adapter.draw_rect(
            rect=bounds,
            stroke=node.style.stroke_color or node.style.color,
            stroke_width=node.style.stroke_width or 1.0,
            radius=radius,
        )
        return

    _paint_table_cells(adapter, item, cell_boxes)


def _paint_table_cells(adapter: ReportLabCanvasAdapter, item: RenderItem, cell_boxes: list[TableCellBox]) -> None:
    node = item.node
    border_color = node.style.stroke_color or node.style.color
    column_count = _column_count_for_boxes(cell_boxes)
    row_count = _row_count_for_boxes(cell_boxes)
    cell_rects: list[tuple[TableCellBox, Rect]] = []

    for cell_box in cell_boxes:
        cell_rect = Rect(x=cell_box.x, y=cell_box.y, width=cell_box.width, height=cell_box.height)
        cell_rects.append((cell_box, cell_rect))
        with adapter.isolated_state():
            adapter.draw_rect(
                rect=cell_rect,
                fill=cell_box.background,
            )
        with adapter.isolated_state():
            adapter.apply_clip_rect(cell_rect)
            content_width = max(1.0, cell_rect.width - cell_box.padding.horizontal)
            content_x = cell_rect.x + cell_box.padding.left
            if cell_box.rich_content is not None:
                rich_node = layout_rich_cell_content(cell_box.rich_content, content_width, content_x, cell_rect.y + cell_box.padding.top)
                content_y = _aligned_content_y(cell_box, rich_node.resolved_height)
                rich_node = layout_rich_cell_content(cell_box.rich_content, content_width, content_x, content_y)
                for rich_item in build_render_list(rich_node):
                    paint_render_item(adapter, rich_item)
            else:
                rendered_text = _plain_cell_paint_text(cell_box, content_width)
                content_y = _aligned_content_y(cell_box, _plain_cell_paint_height(cell_box, rendered_text, content_width))
                adapter.draw_text(
                    x=content_x,
                    y=content_y,
                    width=content_width,
                    text=rendered_text,
                    font_name=cell_box.font_name,
                    font_size=cell_box.font_size,
                    line_height=cell_box.line_height,
                    typography=cell_box.typography,
                    text_direction=cell_box.text_direction,
                    color=cell_box.color,
                    align=cell_box.align,
                    text_overflow=cell_box.text_overflow,
                )

    if node.content.get("border_collapse") is True:
        _paint_collapsed_cell_borders(adapter, item, cell_rects, border_color, row_count, column_count)
        return

    for cell_box, cell_rect in cell_rects:
        if cell_box.border_width is None:
            _paint_cell_border(adapter, item, cell_box, cell_rect, border_color, row_count, column_count)
    for cell_box, cell_rect in cell_rects:
        if cell_box.border_width is not None:
            _paint_cell_border(adapter, item, cell_box, cell_rect, border_color, row_count, column_count)


def _plain_cell_paint_text(cell_box: TableCellBox, content_width: float) -> str:
    if cell_box.text_overflow == "clip":
        return normalize_plain_overflow_text(cell_box.text)
    if cell_box.text_overflow == "ellipsis":
        return fit_plain_overflow_text(
            cell_box.text,
            content_width,
            cell_box.font_name,
            cell_box.font_size,
            cell_box.typography,
            cell_box.text_direction,
        )
    return cell_box.text


def _plain_cell_paint_height(cell_box: TableCellBox, text: str, content_width: float) -> float:
    if cell_box.text_overflow in {"clip", "ellipsis"}:
        return cell_box.line_height
    lines = wrap_text(text, content_width, cell_box.font_name, cell_box.font_size, typography=cell_box.typography, text_direction=cell_box.text_direction)
    return max(1, len(lines)) * cell_box.line_height


def _aligned_content_y(cell_box: TableCellBox, content_height: float) -> float:
    available_height = max(0.0, cell_box.height - cell_box.padding.vertical)
    extra_height = max(0.0, available_height - content_height)
    if cell_box.valign == "middle":
        return cell_box.y + cell_box.padding.top + (extra_height / 2.0)
    if cell_box.valign == "bottom":
        return cell_box.y + cell_box.padding.top + extra_height
    return cell_box.y + cell_box.padding.top


def _paint_cell_border(
    adapter: ReportLabCanvasAdapter,
    item: RenderItem,
    cell_box: TableCellBox,
    cell_rect: Rect,
    fallback_color: RGBA | None,
    row_count: int,
    column_count: int,
) -> None:
    node = item.node
    border_color = cell_box.border_color or fallback_color
    if border_color is None:
        return
    base_width = _table_border_width(node)
    default_inner = node.content.get("inner_border_width")
    default_outer = node.content.get("outer_border_width")
    if cell_box.border_width is not None:
        inner_width = cell_box.border_width
        outer_width = cell_box.border_width
    else:
        inner_width = float(default_inner) if isinstance(default_inner, (int, float)) else base_width
        outer_width = float(default_outer) if isinstance(default_outer, (int, float)) else base_width
    top_width = outer_width if cell_box.row_index == 0 else inner_width
    left_width = outer_width if cell_box.column_index == 0 else inner_width
    bottom_width = outer_width if cell_box.row_index + cell_box.rowspan >= row_count else inner_width
    right_width = outer_width if cell_box.column_index + cell_box.colspan >= column_count else inner_width
    adapter.draw_line(cell_rect.x, cell_rect.y, cell_rect.right, cell_rect.y, border_color, top_width)
    adapter.draw_line(cell_rect.x, cell_rect.bottom, cell_rect.right, cell_rect.bottom, border_color, bottom_width)
    adapter.draw_line(cell_rect.x, cell_rect.y, cell_rect.x, cell_rect.bottom, border_color, left_width)
    adapter.draw_line(cell_rect.right, cell_rect.y, cell_rect.right, cell_rect.bottom, border_color, right_width)


def _paint_collapsed_cell_borders(
    adapter: ReportLabCanvasAdapter,
    item: RenderItem,
    cell_rects: list[tuple[TableCellBox, Rect]],
    fallback_color: RGBA | None,
    row_count: int,
    column_count: int,
) -> None:
    x_breaks = _unique_sorted([rect.x for _cell, rect in cell_rects] + [rect.right for _cell, rect in cell_rects])
    y_breaks = _unique_sorted([rect.y for _cell, rect in cell_rects] + [rect.bottom for _cell, rect in cell_rects])
    segments: dict[tuple[Orientation, float, float, float], _BorderCandidate] = {}
    for cell_box, cell_rect in cell_rects:
        top_width, right_width, bottom_width, left_width = _cell_border_widths(item, cell_box, row_count, column_count)
        color = cell_box.border_color or fallback_color
        _add_collapsed_edge(segments, "horizontal", cell_rect.y, cell_rect.x, cell_rect.right, x_breaks, _BorderCandidate(color, top_width, cell_box.row_index, cell_box.column_index))
        _add_collapsed_edge(segments, "vertical", cell_rect.right, cell_rect.y, cell_rect.bottom, y_breaks, _BorderCandidate(color, right_width, cell_box.row_index, cell_box.column_index))
        _add_collapsed_edge(segments, "horizontal", cell_rect.bottom, cell_rect.x, cell_rect.right, x_breaks, _BorderCandidate(color, bottom_width, cell_box.row_index, cell_box.column_index))
        _add_collapsed_edge(segments, "vertical", cell_rect.x, cell_rect.y, cell_rect.bottom, y_breaks, _BorderCandidate(color, left_width, cell_box.row_index, cell_box.column_index))

    for orientation, fixed, start, end in sorted(segments):
        candidate = segments[(orientation, fixed, start, end)]
        if candidate.color is None:
            continue
        if orientation == "horizontal":
            adapter.draw_line(start, fixed, end, fixed, candidate.color, candidate.width)
        else:
            adapter.draw_line(fixed, start, fixed, end, candidate.color, candidate.width)


def _add_collapsed_edge(
    segments: dict[tuple[Orientation, float, float, float], _BorderCandidate],
    orientation: Orientation,
    fixed: float,
    start: float,
    end: float,
    breaks: list[float],
    candidate: _BorderCandidate,
) -> None:
    points = [start] + [point for point in breaks if start < point < end] + [end]
    for index in range(len(points) - 1):
        segment_start = points[index]
        segment_end = points[index + 1]
        if segment_end <= segment_start:
            continue
        key = (orientation, fixed, segment_start, segment_end)
        current = segments.get(key)
        if current is None or _border_candidate_key(candidate) >= _border_candidate_key(current):
            segments[key] = candidate


def _border_candidate_key(candidate: _BorderCandidate) -> tuple[float, int, int]:
    return (candidate.width, candidate.row_index, candidate.column_index)


def _cell_border_widths(item: RenderItem, cell_box: TableCellBox, row_count: int, column_count: int) -> tuple[float, float, float, float]:
    node = item.node
    base_width = _table_border_width(node)
    default_inner = node.content.get("inner_border_width")
    default_outer = node.content.get("outer_border_width")
    if cell_box.border_width is not None:
        inner_width = cell_box.border_width
        outer_width = cell_box.border_width
    else:
        inner_width = float(default_inner) if isinstance(default_inner, (int, float)) else base_width
        outer_width = float(default_outer) if isinstance(default_outer, (int, float)) else base_width
    top_width = outer_width if cell_box.row_index == 0 else inner_width
    right_width = outer_width if cell_box.column_index + cell_box.colspan >= column_count else inner_width
    bottom_width = outer_width if cell_box.row_index + cell_box.rowspan >= row_count else inner_width
    left_width = outer_width if cell_box.column_index == 0 else inner_width
    return top_width, right_width, bottom_width, left_width


def _unique_sorted(values: list[float]) -> list[float]:
    return sorted(set(values))


def _column_count_for_boxes(cell_boxes: list[TableCellBox]) -> int:
    return max((cell.column_index + cell.colspan for cell in cell_boxes), default=0)


def _row_count_for_boxes(cell_boxes: list[TableCellBox]) -> int:
    return max((cell.row_index + cell.rowspan for cell in cell_boxes), default=0)


def _table_border_width(node: object) -> float:
    if not hasattr(node, "content") or not hasattr(node, "style"):
        return 1.0
    content = getattr(node, "content")
    style = getattr(node, "style")
    if isinstance(content, dict):
        border_width = content.get("border_width")
        if isinstance(border_width, (int, float)):
            return float(border_width)
    stroke_width = getattr(style, "stroke_width", 0.0)
    return float(stroke_width) if isinstance(stroke_width, (int, float)) and stroke_width > 0 else 1.0


PAINTERS: dict[str, Painter] = {
    "text": paint_text,
    "rich_text": paint_rich_text,
    "image": paint_image,
    "rect": paint_rect,
    "line": paint_line,
    "canvas": paint_canvas_background,
    "frame": paint_canvas_background,
    "table": paint_table,
}
