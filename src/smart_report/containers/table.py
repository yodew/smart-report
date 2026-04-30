"""Simple table container/builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import Edges, LayoutNode, Style
from ..style.color import RGBA, parse_color
from ..style.units import Fixed, SizeInput, parse_size

ColorInput = str | RGBA | None


class Table(NodeBuilder):
    def __init__(self, rows: list[list[str]]) -> None:
        style = Style(width=parse_size("100%"), height=parse_size("auto"))
        node = LayoutNode(
            node_type="table",
            style=style,
            content={
                "rows": rows,
                "header_rows": 1,
                "repeat_header": True,
                "cell_padding": Edges.all(6.0),
            },
        )
        super().__init__(node)

    def rows(self, values: list[list[str]]) -> "Table":
        self.node.content["rows"] = values
        return self

    def column_widths(self, values: list[SizeInput]) -> "Table":
        self.node.content["column_widths"] = values
        return self

    def align(self, value: str | list[str]) -> "Table":
        self.node.content["align"] = value
        return self

    def cell_padding(
        self,
        value: SizeInput | None = None,
        *,
        top: SizeInput | None = None,
        right: SizeInput | None = None,
        bottom: SizeInput | None = None,
        left: SizeInput | None = None,
        vertical: SizeInput | None = None,
        horizontal: SizeInput | None = None,
    ) -> "Table":
        self.node.content["cell_padding"] = _parse_table_edges(
            value,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
            vertical=vertical,
            horizontal=horizontal,
        )
        return self

    def header_padding(
        self,
        value: SizeInput | None = None,
        *,
        top: SizeInput | None = None,
        right: SizeInput | None = None,
        bottom: SizeInput | None = None,
        left: SizeInput | None = None,
        vertical: SizeInput | None = None,
        horizontal: SizeInput | None = None,
    ) -> "Table":
        self.node.content["header_cell_padding"] = _parse_table_edges(
            value,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
            vertical=vertical,
            horizontal=horizontal,
        )
        return self

    def header(
        self,
        rows: int = 1,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        repeat: bool = True,
    ) -> "Table":
        self.node.content["header_rows"] = max(0, rows)
        self.node.content["repeat_header"] = repeat
        if background is not None:
            self.node.content["header_background"] = parse_color(background)
        if color is not None:
            self.node.content["header_color"] = parse_color(color)
        return self

    def header_style(
        self,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        font: str | None = None,
        font_size: float | None = None,
        line_height: float | None = None,
        align: str | list[str] | None = None,
    ) -> "Table":
        if background is not None:
            self.node.content["header_background"] = parse_color(background)
        if color is not None:
            self.node.content["header_color"] = parse_color(color)
        if font is not None:
            self.node.content["header_font_name"] = font
        if font_size is not None:
            self.node.content["header_font_size"] = float(font_size)
        if line_height is not None:
            self.node.content["header_line_height"] = float(line_height)
        if align is not None:
            self.node.content["header_align"] = align
        return self

    def zebra(self, background: ColorInput = "#f8fafc") -> "Table":
        self.node.content["zebra_background"] = parse_color(background)
        return self

    def repeat_header(self, value: bool = True) -> "Table":
        self.node.content["repeat_header"] = value
        return self

    def row_style(
        self,
        index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
    ) -> "Table":
        styles = _style_map(self.node.content, "row_styles")
        styles[index] = _merge_style_override(styles.get(index), background=background, color=color, align=align)
        return self

    def column_style(
        self,
        index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
    ) -> "Table":
        styles = _style_map(self.node.content, "column_styles")
        styles[index] = _merge_style_override(styles.get(index), background=background, color=color, align=align)
        return self

    def cell_style(
        self,
        row_index: int,
        column_index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
    ) -> "Table":
        styles = _style_map(self.node.content, "cell_styles")
        key = f"{row_index}:{column_index}"
        styles[key] = _merge_style_override(styles.get(key), background=background, color=color, align=align)
        return self


def _edge_points(value: SizeInput) -> float:
    parsed = parse_size(value)
    if not isinstance(parsed, Fixed):
        raise ValueError("Table cell padding requires fixed point-compatible values")
    return parsed.points


def _parse_table_edges(
    value: SizeInput | None,
    *,
    top: SizeInput | None = None,
    right: SizeInput | None = None,
    bottom: SizeInput | None = None,
    left: SizeInput | None = None,
    vertical: SizeInput | None = None,
    horizontal: SizeInput | None = None,
) -> Edges:
    if value is not None and any(edge is not None for edge in (top, right, bottom, left, vertical, horizontal)):
        raise ValueError("Use either positional cell padding or named cell padding values, not both")
    if value is not None:
        points = _edge_points(value)
        return Edges.all(points)

    resolved_top = top if top is not None else vertical if vertical is not None else 0
    resolved_right = right if right is not None else horizontal if horizontal is not None else 0
    resolved_bottom = bottom if bottom is not None else vertical if vertical is not None else 0
    resolved_left = left if left is not None else horizontal if horizontal is not None else 0
    return Edges(
        top=_edge_points(resolved_top),
        right=_edge_points(resolved_right),
        bottom=_edge_points(resolved_bottom),
        left=_edge_points(resolved_left),
    )


def _style_map(content: dict[str, object], key: str) -> dict[object, object]:
    value = content.get(key)
    if isinstance(value, dict):
        return value
    styles: dict[object, object] = {}
    content[key] = styles
    return styles


def _merge_style_override(
    existing: object,
    *,
    background: ColorInput = None,
    color: ColorInput = None,
    align: str | None = None,
) -> dict[str, object]:
    style: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
    if background is not None:
        style["background"] = parse_color(background)
    if color is not None:
        style["color"] = parse_color(color)
    if align is not None:
        style["align"] = align
    return style
