"""Simple table container/builder."""

from __future__ import annotations

from collections.abc import Sequence

from .._builder_core import NodeBuilder
from ..layout.node import Edges, LayoutNode, Style
from ..style.color import RGBA, parse_color
from ..style.units import Fixed, SizeInput, parse_size

ColorInput = str | RGBA | None


class Table(NodeBuilder):
    def __init__(self, rows: Sequence[Sequence[object]]) -> None:
        style = Style(width=parse_size("100%"), height=parse_size("auto"))
        node = LayoutNode(
            node_type="table",
            style=style,
            content={
                "rows": _normalize_rows(rows),
                "header_rows": 1,
                "repeat_header": True,
                "cell_padding": Edges.all(6.0),
            },
        )
        super().__init__(node)

    def rows(self, values: Sequence[Sequence[object]]) -> "Table":
        self.node.content["rows"] = _normalize_rows(values)
        return self

    def cell(self, row_index: int, column_index: int, value: object) -> "Table":
        rows = self.node.content.get("rows")
        if not isinstance(rows, list):
            raise ValueError("Table rows are not initialized")
        while len(rows) <= row_index:
            rows.append([])
        row = rows[row_index]
        if not isinstance(row, list):
            raise ValueError(f"Table row is not a list: {row_index}")
        while len(row) <= column_index:
            row.append("")
        row[column_index] = value.build() if isinstance(value, NodeBuilder) else value
        return self

    def column_widths(self, values: list[SizeInput]) -> "Table":
        self.node.content["column_widths"] = values
        return self

    def align(self, value: str | list[str]) -> "Table":
        _validate_align_value(value)
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
            _validate_align_value(align)
            self.node.content["header_align"] = align
        return self

    def footer(
        self,
        rows: Sequence[Sequence[object]],
        *,
        repeat: bool = False,
        background: ColorInput = None,
        color: ColorInput = None,
    ) -> "Table":
        self.node.content["footer_rows"] = _normalize_rows(rows)
        self.node.content["repeat_footer"] = repeat
        if background is not None:
            self.node.content["footer_background"] = parse_color(background)
        if color is not None:
            self.node.content["footer_color"] = parse_color(color)
        return self

    def footer_style(
        self,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | list[str] | None = None,
    ) -> "Table":
        if background is not None:
            self.node.content["footer_background"] = parse_color(background)
        if color is not None:
            self.node.content["footer_color"] = parse_color(color)
        if align is not None:
            _validate_align_value(align)
            self.node.content["footer_align"] = align
        return self

    def subtotal(self, row: list[object], *, background: ColorInput = "#f1f5f9") -> "Table":
        return self.footer([row], repeat=False, background=background)

    def borders(
        self,
        color: ColorInput = "#cbd5e1",
        *,
        width: float = 1.0,
        inner_width: float | None = None,
        outer_width: float | None = None,
    ) -> "Table":
        self.node.content["border_color"] = parse_color(color)
        self.node.content["border_width"] = float(width)
        if inner_width is not None:
            self.node.content["inner_border_width"] = float(inner_width)
        if outer_width is not None:
            self.node.content["outer_border_width"] = float(outer_width)
        return self

    def cell_border(self, row_index: int, column_index: int, *, color: ColorInput = None, width: float = 1.0) -> "Table":
        styles = _style_map(self.node.content, "cell_styles")
        key = f"{row_index}:{column_index}"
        existing = styles.get(key)
        style: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
        if color is not None:
            style["border_color"] = parse_color(color)
        style["border_width"] = float(width)
        styles[key] = style
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

    def span(self, row_index: int, column_index: int, *, rowspan: int = 1, colspan: int = 1) -> "Table":
        if rowspan < 1 or colspan < 1:
            raise ValueError("Table span values must be >= 1")
        spans = _style_map(self.node.content, "cell_spans")
        spans[f"{row_index}:{column_index}"] = {"rowspan": rowspan, "colspan": colspan}
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
        _validate_align(align)
        style["align"] = align
    return style


def _validate_align(value: str) -> None:
    if value.lower() not in {"left", "center", "right"}:
        raise ValueError(f"Unsupported table alignment: {value}")


def _validate_align_value(value: str | list[str]) -> None:
    if isinstance(value, str):
        _validate_align(value)
        return
    for item in value:
        _validate_align(item)


def _normalize_rows(rows: Sequence[Sequence[object]]) -> list[list[object]]:
    normalized: list[list[object]] = []
    for row in rows:
        normalized.append([cell.build() if isinstance(cell, NodeBuilder) else cell for cell in row])
    return normalized
