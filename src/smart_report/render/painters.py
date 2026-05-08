"""Painter registry for render items."""

from __future__ import annotations

from typing import Callable

from ..layout.node import Rect, RenderItem
from ..layout.pass4_render import build_render_list
from ..layout.table_model import TableCellBox, layout_rich_cell_content, table_cell_boxes
from ..style.color import RGBA
from .rl_adapter import ReportLabCanvasAdapter

Painter = Callable[[ReportLabCanvasAdapter, RenderItem], None]


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
    adapter.draw_text(
        x=bounds.x + padding.left,
        y=bounds.y + padding.top,
        width=max(1.0, bounds.width - padding.horizontal),
        text=text_value,
        font_name=node.style.font_name,
        font_size=node.style.font_size,
        line_height=node.style.line_height,
        typography=node.style.typography,
        text_direction=node.style.text_direction,
        color=node.style.color,
    )


def paint_image(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    image_source = item.node.content.get("src_bytes") or item.node.content.get("src")
    if not isinstance(image_source, (str, bytes)):
        return
    fit = item.node.content.get("object_fit", "stretch")
    object_fit = fit if isinstance(fit, str) else "stretch"
    radius = item.node.style.border_radius
    if radius > 0:
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
    if radius > 0:
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
            content_y = cell_rect.y + cell_box.padding.top
            if cell_box.rich_content is not None:
                rich_node = layout_rich_cell_content(cell_box.rich_content, content_width, content_x, content_y)
                for rich_item in build_render_list(rich_node):
                    paint_render_item(adapter, rich_item)
            else:
                adapter.draw_text(
                    x=content_x,
                    y=content_y,
                    width=content_width,
                    text=cell_box.text,
                    font_name=cell_box.font_name,
                    font_size=cell_box.font_size,
                    line_height=cell_box.line_height,
                    typography=cell_box.typography,
                    text_direction=cell_box.text_direction,
                    color=cell_box.color,
                    align=cell_box.align,
                )

    for cell_box, cell_rect in cell_rects:
        if cell_box.border_width is None:
            _paint_cell_border(adapter, item, cell_box, cell_rect, border_color, row_count, column_count)
    for cell_box, cell_rect in cell_rects:
        if cell_box.border_width is not None:
            _paint_cell_border(adapter, item, cell_box, cell_rect, border_color, row_count, column_count)


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
    "image": paint_image,
    "rect": paint_rect,
    "line": paint_line,
    "canvas": paint_canvas_background,
    "frame": paint_canvas_background,
    "table": paint_table,
}
