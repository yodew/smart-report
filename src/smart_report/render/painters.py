"""Painter registry for render items."""

from __future__ import annotations

from typing import Callable

from ..layout.node import Rect, RenderItem
from ..layout.table_model import TableCellBox, table_cell_boxes
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
        color=node.style.color,
    )


def paint_image(adapter: ReportLabCanvasAdapter, item: RenderItem) -> None:
    image_path = item.node.content.get("src")
    if not isinstance(image_path, str):
        return
    adapter.draw_image(image_path, item.absolute_bounds, opacity=item.node.style.opacity)


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

    for cell_box in cell_boxes:
        cell_rect = Rect(x=cell_box.x, y=cell_box.y, width=cell_box.width, height=cell_box.height)
        adapter.draw_rect(
            rect=cell_rect,
            fill=cell_box.background,
            stroke=border_color,
            stroke_width=node.style.stroke_width or 1.0,
        )
        with adapter.isolated_state():
            adapter.apply_clip_rect(cell_rect)
            adapter.draw_text(
                x=cell_rect.x + cell_box.padding.left,
                y=cell_rect.y + cell_box.padding.top,
                width=max(1.0, cell_rect.width - cell_box.padding.horizontal),
                text=cell_box.text,
                font_name=cell_box.font_name,
                font_size=cell_box.font_size,
                line_height=cell_box.line_height,
                color=cell_box.color,
                align=cell_box.align,
            )


PAINTERS: dict[str, Painter] = {
    "text": paint_text,
    "image": paint_image,
    "rect": paint_rect,
    "line": paint_line,
    "canvas": paint_canvas_background,
    "table": paint_table,
}
