"""Simple table container/builder."""

from __future__ import annotations

import math
from collections.abc import Sequence
from os import PathLike

from .._builder_core import NodeBuilder
from ..layout.node import Edges, LayoutNode, Style
from ..style.color import RGBA, parse_color
from ..style.units import Auto, Fixed, Percent, SizeInput, parse_size

ColorInput = str | RGBA | None


class Table(NodeBuilder):
    """Chainable report table builder.

    Rows are a 2D sequence. Cells may be strings/numbers or rich builders such
    as ``Frame``, ``Text``, and ``Image``.
    """

    def __init__(self, rows: Sequence[Sequence[object]]) -> None:
        """Create a table from row data."""

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
        """Replace all table rows."""

        self.node.content["rows"] = _normalize_rows(values)
        return self

    def background_image(self, src: str | bytes | PathLike[str], *, fit: str = "cover", opacity: float = 1.0) -> "Table":
        """Set a table-level background image under cells and borders."""

        return super().background_image(src, fit=fit, opacity=opacity)

    def cell(self, row_index: int, column_index: int, value: object) -> "Table":
        """Set a single cell value, expanding rows/columns as needed."""

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
        """Set column widths.

        Values may be point values, unit strings, percentages, or ``"auto"``.
        """

        self.node.content["column_widths"] = values
        return self

    def row_height(self, row_index: int, height: SizeInput) -> "Table":
        """Set a fixed point-compatible minimum height for one logical row."""

        heights = _style_map(self.node.content, "row_heights")
        heights[row_index] = _height_points(height)
        return self

    def row_heights(self, values: Sequence[SizeInput | None]) -> "Table":
        """Set minimum heights for logical rows by zero-based row index."""

        heights: dict[object, object] = {}
        for row_index, height in enumerate(values):
            if height is not None:
                heights[row_index] = _height_points(height)
        self.node.content["row_heights"] = heights
        return self

    def cell_height(self, row_index: int, column_index: int, height: SizeInput) -> "Table":
        """Set a fixed point-compatible minimum height for one logical cell."""

        heights = _style_map(self.node.content, "cell_heights")
        heights[f"{row_index}:{column_index}"] = _height_points(height)
        return self

    def column_min_widths(self, values: list[SizeInput]) -> "Table":
        """Set per-column minimum widths for auto-fit/clamped sizing."""

        _validate_column_width_constraints("column_min_widths", values)
        self.node.content["column_min_widths"] = values
        return self

    def column_max_widths(self, values: list[SizeInput]) -> "Table":
        """Set per-column maximum widths for auto-fit/clamped sizing."""

        _validate_column_width_constraints("column_max_widths", values)
        self.node.content["column_max_widths"] = values
        return self

    def auto_fit_columns(self, columns: Sequence[int] | None = None) -> "Table":
        """Auto-fit columns by supported cell natural content width.

        Pass ``None`` to auto-fit all columns, or a sequence of zero-based
        column indexes to fit only selected columns. Plain cells plus measurable
        ``Text``, ``RichText``, and simple flow ``Frame`` cells participate;
        unsupported rich cells are ignored conservatively.
        """

        self.node.content["auto_fit_columns"] = _normalize_auto_fit_columns(columns)
        return self

    def align(self, value: str | list[str]) -> "Table":
        """Set horizontal cell text alignment.

        Accepted values are ``"left"``, ``"center"``, and ``"right"``.
        Pass a single value for all columns or a list per column.
        """

        _validate_align_value(value)
        self.node.content["align"] = value
        return self

    def text_overflow(self, value: str) -> "Table":
        """Set plain-text cell overflow behavior.

        Accepted values are ``"wrap"``, ``"clip"``, and ``"ellipsis"``.
        """

        self.node.content["text_overflow"] = _normalize_text_overflow(value)
        return self

    def valign(self, value: str) -> "Table":
        """Set vertical cell content alignment.

        Accepted values are ``"top"``, ``"middle"``, and ``"bottom"``.
        """

        self.node.content["valign"] = _normalize_valign(value)
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
        """Set default cell padding.

        Prefer named arguments such as ``vertical=6`` and ``horizontal=10``.
        """

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
        """Set padding for header cells only."""

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
        """Configure leading header rows.

        ``rows`` is the number of leading body rows treated as headers.
        ``repeat=True`` repeats them on paginated table slices.
        """

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
        """Override style for header cells.

        ``align`` accepts ``"left"``, ``"center"``, ``"right"``, or a list
        of those values per column.
        """

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
        """Add footer rows after the body.

        ``repeat=True`` repeats footer rows on paginated table slices.
        """

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
        font: str | None = None,
        font_size: float | None = None,
        line_height: float | None = None,
        align: str | list[str] | None = None,
    ) -> "Table":
        """Override style for footer cells.

        ``align`` accepts ``"left"``, ``"center"``, ``"right"``, or a list
        of those values per column.
        """

        if background is not None:
            self.node.content["footer_background"] = parse_color(background)
        if color is not None:
            self.node.content["footer_color"] = parse_color(color)
        if font is not None:
            self.node.content["footer_font_name"] = font
        if font_size is not None:
            self.node.content["footer_font_size"] = float(font_size)
        if line_height is not None:
            self.node.content["footer_line_height"] = float(line_height)
        if align is not None:
            _validate_align_value(align)
            self.node.content["footer_align"] = align
        return self

    def subtotal(
        self,
        row: list[object],
        *,
        repeat: bool = False,
        background: ColorInput = "#f1f5f9",
        color: ColorInput = None,
    ) -> "Table":
        """Add a single footer/subtotal row."""

        return self.footer([row], repeat=repeat, background=background, color=color)

    def borders(
        self,
        color: ColorInput = "#cbd5e1",
        *,
        width: float = 1.0,
        inner_width: float | None = None,
        outer_width: float | None = None,
    ) -> "Table":
        """Set table border color and widths.

        To hide borders while keeping text color, use
        ``.borders("transparent", width=0)``.
        """

        self.node.content["border_color"] = parse_color(color)
        self.node.content["border_width"] = float(width)
        if inner_width is not None:
            self.node.content["inner_border_width"] = float(inner_width)
        if outer_width is not None:
            self.node.content["outer_border_width"] = float(outer_width)
        return self

    def border_collapse(self, value: bool = True) -> "Table":
        """Collapse adjacent cell borders so shared edges paint once."""

        self.node.content["border_collapse"] = value
        return self

    def cell_border(self, row_index: int, column_index: int, *, color: ColorInput = None, width: float = 1.0) -> "Table":
        """Override border color and width for one cell."""

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
        """Set alternating row background color."""

        self.node.content["zebra_background"] = parse_color(background)
        return self

    def repeat_header(self, value: bool = True) -> "Table":
        """Enable or disable repeating header rows during pagination."""

        self.node.content["repeat_header"] = value
        return self

    def row_style(
        self,
        index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
        font: str | None = None,
        font_size: float | None = None,
        line_height: float | None = None,
        text_overflow: str | None = None,
        valign: str | None = None,
    ) -> "Table":
        """Override style for one logical row by zero-based row index.

        ``align`` accepts ``"left"``, ``"center"``, or ``"right"``.
        ``text_overflow`` accepts ``"wrap"``, ``"clip"``, or
        ``"ellipsis"``. ``valign`` accepts ``"top"``, ``"middle"``, or
        ``"bottom"``.
        """

        styles = _style_map(self.node.content, "row_styles")
        styles[index] = _merge_style_override(
            styles.get(index),
            background=background,
            color=color,
            align=align,
            font=font,
            font_size=font_size,
            line_height=line_height,
            text_overflow=text_overflow,
            valign=valign,
        )
        return self

    def column_style(
        self,
        index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
        font: str | None = None,
        font_size: float | None = None,
        line_height: float | None = None,
        text_overflow: str | None = None,
        valign: str | None = None,
    ) -> "Table":
        """Override style for one column by zero-based column index.

        ``align`` accepts ``"left"``, ``"center"``, or ``"right"``.
        ``text_overflow`` accepts ``"wrap"``, ``"clip"``, or
        ``"ellipsis"``. ``valign`` accepts ``"top"``, ``"middle"``, or
        ``"bottom"``.
        """

        styles = _style_map(self.node.content, "column_styles")
        styles[index] = _merge_style_override(
            styles.get(index),
            background=background,
            color=color,
            align=align,
            font=font,
            font_size=font_size,
            line_height=line_height,
            text_overflow=text_overflow,
            valign=valign,
        )
        return self

    def cell_style(
        self,
        row_index: int,
        column_index: int,
        *,
        background: ColorInput = None,
        color: ColorInput = None,
        align: str | None = None,
        font: str | None = None,
        font_size: float | None = None,
        line_height: float | None = None,
        text_overflow: str | None = None,
        valign: str | None = None,
    ) -> "Table":
        """Override style for one cell by zero-based row and column index.

        ``align`` accepts ``"left"``, ``"center"``, or ``"right"``.
        ``text_overflow`` accepts ``"wrap"``, ``"clip"``, or
        ``"ellipsis"``. ``valign`` accepts ``"top"``, ``"middle"``, or
        ``"bottom"``.
        """

        styles = _style_map(self.node.content, "cell_styles")
        key = f"{row_index}:{column_index}"
        styles[key] = _merge_style_override(
            styles.get(key),
            background=background,
            color=color,
            align=align,
            font=font,
            font_size=font_size,
            line_height=line_height,
            text_overflow=text_overflow,
            valign=valign,
        )
        return self

    def span(self, row_index: int, column_index: int, *, rowspan: int = 1, colspan: int = 1) -> "Table":
        """Make a cell span rows and/or columns."""

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


def _height_points(value: SizeInput) -> float:
    parsed = parse_size(value)
    if not isinstance(parsed, Fixed):
        raise ValueError("Table row and cell heights require fixed point-compatible values")
    points = parsed.points
    if not math.isfinite(points):
        raise ValueError("Table row and cell heights must be finite")
    if points < 0:
        raise ValueError("Table row and cell heights must be non-negative")
    return points


def _validate_column_width_constraints(key: str, values: list[SizeInput]) -> None:
    for value in values:
        parsed = parse_size(value)
        if isinstance(parsed, Auto):
            raise ValueError(f"Table {key} constraints cannot be auto")
        if isinstance(parsed, Fixed):
            amount = parsed.points
        elif isinstance(parsed, Percent):
            amount = parsed.ratio
        else:
            amount = 0.0
        if not math.isfinite(amount):
            raise ValueError(f"Table {key} constraints must be finite")
        if amount < 0:
            raise ValueError(f"Table {key} constraints must be non-negative")


def _normalize_auto_fit_columns(columns: object) -> bool | list[int]:
    if columns is None:
        return True
    if not isinstance(columns, Sequence):
        raise TypeError("Table auto_fit_columns columns must be a sequence of integer indexes")
    normalized: list[int] = []
    for column in columns:
        if not isinstance(column, int) or isinstance(column, bool):
            raise TypeError("Table auto_fit_columns columns must be integer indexes")
        if column < 0:
            raise ValueError("Table auto_fit_columns columns must be non-negative")
        normalized.append(column)
    return sorted(set(normalized))


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
    font: str | None = None,
    font_size: float | None = None,
    line_height: float | None = None,
    text_overflow: str | None = None,
    valign: str | None = None,
) -> dict[str, object]:
    style: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
    if background is not None:
        style["background"] = parse_color(background)
    if color is not None:
        style["color"] = parse_color(color)
    if align is not None:
        _validate_align(align)
        style["align"] = align
    if font is not None:
        style["font_name"] = font
    if font_size is not None:
        style["font_size"] = float(font_size)
    if line_height is not None:
        style["line_height"] = float(line_height)
    if text_overflow is not None:
        style["text_overflow"] = _normalize_text_overflow(text_overflow)
    if valign is not None:
        style["valign"] = _normalize_valign(valign)
    return style


def _normalize_text_overflow(value: str) -> str:
    normalized = value.lower()
    if normalized not in {"wrap", "clip", "ellipsis"}:
        raise ValueError(f"Unsupported table text overflow: {value}")
    return normalized


def _normalize_valign(value: str) -> str:
    normalized = value.lower()
    if normalized not in {"top", "middle", "bottom"}:
        raise ValueError(f"Unsupported table vertical alignment: {value}")
    return normalized


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
