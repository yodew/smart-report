"""Internal chainable builder API for smart-report."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from math import isfinite
from os import PathLike, fspath
from typing import TYPE_CHECKING, TypeVar, cast

from .document import Document
from .document_builder import DocumentBuilder, document
from .section import SectionBuilder
from .layout.node import CornerRadii, Edges, LayoutNode, OverflowMode, PositionMode, Style
from .style.color import parse_color
from .style.font import DEFAULT_FONT_REGISTRY
from .style.typography import normalize_text_direction, normalize_typography_mode
from .style.units import Fixed, SizeInput, parse_size

if TYPE_CHECKING:
    from .containers.canvas import Canvas
    from .containers.frame import Frame
    from .containers.table import Table
    from .elements.image import Image
    from .elements.rich_text import RichText
    from .elements.shape import Line, Rect
    from .elements.spacer import Spacer
    from .elements.text import Text


BuilderT = TypeVar("BuilderT", bound="NodeBuilder")
ContainerT = TypeVar("ContainerT", bound="ContainerBuilder")
EdgeInput = SizeInput | tuple[SizeInput, ...]
RadiusInput = SizeInput | tuple[SizeInput, ...]
BackgroundImageSource = str | bytes | PathLike[str]

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (595.2756, 841.8898),
    "LETTER": (612.0, 792.0),
}
MAX_LAYOUT_TRACKS = 64


def _edge_points(value: SizeInput) -> float:
    parsed = parse_size(value)
    if not isinstance(parsed, Fixed):
        raise ValueError("Padding and margin require fixed point-compatible values")
    if not isfinite(parsed.points):
        raise ValueError("Size values must be finite")
    return parsed.points


def _parse_edges(value: EdgeInput) -> Edges:
    if isinstance(value, tuple):
        if len(value) == 2:
            vertical, horizontal = value
            return Edges(
                top=_edge_points(vertical),
                right=_edge_points(horizontal),
                bottom=_edge_points(vertical),
                left=_edge_points(horizontal),
            )
        if len(value) == 4:
            top, right, bottom, left = value
            return Edges(
                top=_edge_points(top),
                right=_edge_points(right),
                bottom=_edge_points(bottom),
                left=_edge_points(left),
            )
        raise ValueError("Edges tuple must have 2 or 4 values")

    return Edges.all(_edge_points(value))


def _parse_explicit_edges(
    value: EdgeInput | None,
    *,
    top: SizeInput | None = None,
    right: SizeInput | None = None,
    bottom: SizeInput | None = None,
    left: SizeInput | None = None,
    vertical: SizeInput | None = None,
    horizontal: SizeInput | None = None,
) -> Edges:
    has_directional_values = any(
        edge_value is not None
        for edge_value in (top, right, bottom, left, vertical, horizontal)
    )
    if value is not None and has_directional_values:
        raise ValueError("Use either positional edge value or named edge values, not both")
    if value is not None:
        return _parse_edges(value)

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


def _radius_points(value: SizeInput) -> float:
    points = _edge_points(value)
    if points < 0:
        raise ValueError("Radius values must be non-negative")
    return points


def _parse_corner_radii(
    value: RadiusInput | None,
    *,
    top_left: SizeInput | None = None,
    top_right: SizeInput | None = None,
    bottom_right: SizeInput | None = None,
    bottom_left: SizeInput | None = None,
) -> CornerRadii:
    has_named_values = any(item is not None for item in (top_left, top_right, bottom_right, bottom_left))
    if value is not None and has_named_values:
        raise ValueError("Use either positional radius value or named corner radii, not both")
    if isinstance(value, tuple):
        if len(value) != 4:
            raise ValueError("Radius tuple must contain top_left, top_right, bottom_right, bottom_left")
        return CornerRadii(
            top_left=_radius_points(value[0]),
            top_right=_radius_points(value[1]),
            bottom_right=_radius_points(value[2]),
            bottom_left=_radius_points(value[3]),
        )
    if value is not None:
        return CornerRadii.all(_radius_points(value))
    return CornerRadii(
        top_left=_radius_points(top_left if top_left is not None else 0),
        top_right=_radius_points(top_right if top_right is not None else 0),
        bottom_right=_radius_points(bottom_right if bottom_right is not None else 0),
        bottom_left=_radius_points(bottom_left if bottom_left is not None else 0),
    )


class NodeBuilder:
    """Base class for chainable element/container builders.

    Most public builders inherit these methods, so calls such as
    ``.size(...)``, ``.absolute(...)``, ``.background(...)``, ``.z(...)``,
    ``.font_size(...)``, and ``.padding(...)`` can be chained on text,
    frames, canvases, tables, images, and shapes where applicable.
    """

    node: LayoutNode

    def __init__(self, node: LayoutNode) -> None:
        self.node = node

    def name(self: BuilderT, value: str) -> BuilderT:
        """Set an optional debug name for this node."""

        self.node.name = value
        return self

    def width(self: BuilderT, value: SizeInput) -> BuilderT:
        """Set node width.

        Values may be points, unit strings such as ``"10mm"``, percentages
        such as ``"100%"``, or ``"auto"``.
        """

        self.node.style.width = parse_size(value)
        return self

    def height(self: BuilderT, value: SizeInput) -> BuilderT:
        """Set node height.

        Values may be points, unit strings such as ``"2cm"``, percentages,
        or ``"auto"``.
        """

        self.node.style.height = parse_size(value)
        return self

    def size(self: BuilderT, width: SizeInput, height: SizeInput) -> BuilderT:
        """Set width and height together."""

        self.node.style.width = parse_size(width)
        self.node.style.height = parse_size(height)
        return self

    def padding(
        self: BuilderT,
        value: EdgeInput | None = None,
        *,
        top: SizeInput | None = None,
        right: SizeInput | None = None,
        bottom: SizeInput | None = None,
        left: SizeInput | None = None,
        vertical: SizeInput | None = None,
        horizontal: SizeInput | None = None,
    ) -> BuilderT:
        """Set padding.

        Tuple compatibility:
        - ``padding(all)``
        - ``padding((vertical, horizontal))``
        - ``padding((top, right, bottom, left))``

        Prefer named arguments for clarity, e.g. ``padding(top=24, right=16)``.
        """

        self.node.style.padding = _parse_explicit_edges(
            value,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
            vertical=vertical,
            horizontal=horizontal,
        )
        _ = self.node.content.pop("base_padding", None)
        return self

    def margin(
        self: BuilderT,
        value: EdgeInput | None = None,
        *,
        top: SizeInput | None = None,
        right: SizeInput | None = None,
        bottom: SizeInput | None = None,
        left: SizeInput | None = None,
        vertical: SizeInput | None = None,
        horizontal: SizeInput | None = None,
    ) -> BuilderT:
        """Set margin.

        Tuple compatibility:
        - ``margin(all)``
        - ``margin((vertical, horizontal))``
        - ``margin((top, right, bottom, left))``

        Prefer named arguments for clarity, e.g. ``margin(top=24, right=24, bottom=20, left=24)``.
        """

        self.node.style.margin = _parse_explicit_edges(
            value,
            top=top,
            right=right,
            bottom=bottom,
            left=left,
            vertical=vertical,
            horizontal=horizontal,
        )
        return self

    def background(self: BuilderT, value: str | None) -> BuilderT:
        """Set background fill color.

        Supports named colors, ``#RRGGBB``, ``#RRGGBBAA``, ``rgb(...)``,
        ``rgba(...)``, ``"transparent"``, or ``None`` for no background.
        """

        self.node.style.background = parse_color(value)
        return self

    def background_image(self: BuilderT, src: BackgroundImageSource, *, fit: str = "cover", opacity: float = 1.0) -> BuilderT:
        """Set a background image for this node.

        Sources may be string paths, ``pathlib.Path`` values, bytes, or
        ``data:image/...;base64,...`` strings. Accepted fit values are
        ``"stretch"``, ``"contain"``, and ``"cover"``.
        """

        if self.node.node_type not in {"canvas", "frame", "table"}:
            raise ValueError("Background images are supported on Frame, Canvas, and Table")
        normalized_fit = fit.lower()
        if normalized_fit not in {"stretch", "contain", "cover"}:
            raise ValueError(f"Unsupported background image fit: {fit}")
        opacity_value = float(opacity)
        if not isfinite(opacity_value) or opacity_value < 0.0 or opacity_value > 1.0:
            raise ValueError("Background image opacity must be finite and between 0.0 and 1.0")

        if isinstance(src, bytes):
            self.node.content["background_image_src_bytes"] = src
            self.node.content.pop("background_image_src", None)
        else:
            try:
                source = fspath(src)
            except TypeError as exc:
                raise TypeError("Background image source must be str, bytes, or PathLike[str]") from exc
            if source.startswith("data:image/"):
                _prefix, _separator, payload = source.partition(",")
                self.node.content["background_image_src_bytes"] = base64.b64decode(payload)
                self.node.content.pop("background_image_src", None)
            else:
                self.node.content["background_image_src"] = source
                self.node.content.pop("background_image_src_bytes", None)
        self.node.content["background_image_fit"] = normalized_fit
        self.node.content["background_image_opacity"] = opacity_value
        return self

    def color(self: BuilderT, value: str | None) -> BuilderT:
        """Set foreground/text color using the shared color syntax."""

        self.node.style.color = parse_color(value)
        return self

    def opacity(self: BuilderT, value: float) -> BuilderT:
        """Set overall node opacity from 0.0 to 1.0."""

        self.node.style.opacity = value
        return self

    def z(self: BuilderT, value: int) -> BuilderT:
        """Set z-index; larger values paint above smaller values."""

        self.node.style.z_index = value
        return self

    def overflow(self: BuilderT, value: str) -> BuilderT:
        """Set overflow behavior.

        Accepted values are ``"visible"`` and ``"hidden"``. Hidden clips
        child content to this node's bounds.
        """

        self.node.style.overflow = OverflowMode(value)
        return self

    def absolute(self: BuilderT, left: SizeInput = 0, top: SizeInput = 0) -> BuilderT:
        """Position this node absolutely within its parent content box."""

        self.node.style.position = PositionMode.ABSOLUTE
        self.node.style.left = parse_size(left)
        self.node.style.top = parse_size(top)
        return self

    def flow(self: BuilderT) -> BuilderT:
        """Return this node to normal flow layout."""

        self.node.style.position = PositionMode.FLOW
        self.node.style.left = None
        self.node.style.top = None
        return self

    def font(self: BuilderT, name: str) -> BuilderT:
        """Set font name for text rendered by this node."""

        self.node.style.font_name = name
        self.node.style.font_family = None
        return self

    def font_family(self: BuilderT, name: str) -> BuilderT:
        """Set a registered font family name.

        The concrete font is resolved from the registered family, currently
        using the regular face for this builder.
        """

        self.node.style.font_family = name
        self.node.style.font_name = DEFAULT_FONT_REGISTRY.font_name_for_family(name)
        return self

    def font_size(self: BuilderT, size: float) -> BuilderT:
        """Set font size in points.

        If line height has not been explicitly set, it updates to
        ``size * 1.2``.
        """

        self.node.style.font_size = size
        if self.node.style.line_height_auto:
            self.node.style.line_height = size * 1.2
        return self

    def line_height(self: BuilderT, value: float) -> BuilderT:
        """Set explicit line height in points.

        Calling this disables automatic ``font_size * 1.2`` line height.
        """

        self.node.style.line_height = value
        self.node.style.line_height_auto = False
        return self

    def typography(self: BuilderT, value: str) -> BuilderT:
        """Set text shaping/preprocessing mode.

        Accepted values are ``"plain"``, ``"auto"``, and ``"advanced"``.
        """

        self.node.style.typography = normalize_typography_mode(value)
        return self

    def text_direction(self: BuilderT, value: str) -> BuilderT:
        """Set text direction.

        Accepted values are ``"auto"``, ``"ltr"``, and ``"rtl"``.
        """

        self.node.style.text_direction = normalize_text_direction(value)
        return self


    def stroke(self: BuilderT, color: str | None, width: float) -> BuilderT:
        """Set stroke/border color and width."""

        self.node.style.stroke_color = parse_color(color)
        self.node.style.stroke_width = width
        return self

    def radius(
        self: BuilderT,
        value: RadiusInput | None = None,
        *,
        top_left: SizeInput | None = None,
        top_right: SizeInput | None = None,
        bottom_right: SizeInput | None = None,
        bottom_left: SizeInput | None = None,
    ) -> BuilderT:
        """Set corner radius.

        ``radius(8)`` keeps the existing uniform-radius behavior. Use
        ``radius((top_left, top_right, bottom_right, bottom_left))`` or named
        corner arguments to set corners independently. Values must be fixed
        point-compatible and non-negative.
        """

        self.node.style.border_radius = _parse_corner_radii(
            value,
            top_left=top_left,
            top_right=top_right,
            bottom_right=bottom_right,
            bottom_left=bottom_left,
        )
        return self

    def layout(self: BuilderT, value: str) -> BuilderT:
        """Set layout mode directly.

        Accepted values are ``"flow"``, ``"flex"``, ``"grid"``, and
        ``"columns"``. Prefer ``.flex(...)``, ``.grid(...)``, or
        ``.columns(...)`` for normal use.
        """

        normalized = value.lower()
        if normalized not in {"flow", "flex", "grid", "columns"}:
            raise ValueError(f"Unsupported layout mode: {value}")
        self.node.content["layout"] = normalized
        return self

    def gap(self: BuilderT, value: SizeInput) -> BuilderT:
        """Set layout gap used by flex, grid, and columns layouts."""

        self.node.content["gap"] = _edge_points(value)
        return self

    def flex(
        self: BuilderT,
        direction: str = "row",
        *,
        gap: SizeInput | None = None,
        wrap: bool = False,
        justify: str = "start",
        align: str = "start",
        row_gap: SizeInput | None = None,
        column_gap: SizeInput | None = None,
    ) -> BuilderT:
        """Use practical flex row/column layout.

        ``direction`` accepts ``"row"`` or ``"column"``. ``wrap=True`` is
        supported only for row direction. ``justify`` accepts ``"start"``,
        ``"center"``, ``"end"``, ``"space-between"``. ``align`` accepts
        ``"start"``, ``"center"``, ``"end"``.
        """

        normalized = direction.lower()
        if normalized not in {"row", "column"}:
            raise ValueError(f"Unsupported flex direction: {direction}")
        if wrap and normalized != "row":
            raise ValueError("flex wrap is only supported for row direction")

        norm_justify = justify.lower()
        if norm_justify not in {"start", "center", "end", "space-between"}:
            raise ValueError(f"Unsupported flex justify: {justify}")
        norm_align = align.lower()
        if norm_align not in {"start", "center", "end"}:
            raise ValueError(f"Unsupported flex align: {align}")

        self.node.content["layout"] = "flex"
        self.node.content["flex_direction"] = normalized
        if wrap:
            self.node.content["flex_wrap"] = True
        else:
            _ = self.node.content.pop("flex_wrap", None)
        if gap is not None:
            self.node.content["gap"] = _edge_points(gap)
        self.node.content["flex_justify"] = norm_justify
        self.node.content["flex_align"] = norm_align
        if row_gap is not None:
            self.node.content["row_gap"] = _edge_points(row_gap)
        if column_gap is not None:
            self.node.content["column_gap"] = _edge_points(column_gap)
        return self

    def grid(self: BuilderT, columns: int, *, gap: SizeInput | None = None) -> BuilderT:
        """Use fixed-column grid layout."""

        if columns < 1:
            raise ValueError("Grid columns must be >= 1")
        if columns > MAX_LAYOUT_TRACKS:
            raise ValueError(f"Grid columns must be <= {MAX_LAYOUT_TRACKS}")
        self.node.content["layout"] = "grid"
        self.node.content["grid_columns"] = columns
        if gap is not None:
            self.node.content["gap"] = _edge_points(gap)
        return self

    def columns(self: BuilderT, count: int, *, gap: SizeInput | None = None) -> BuilderT:
        """Use multi-column flow layout."""

        if count < 1:
            raise ValueError("Column count must be >= 1")
        if count > MAX_LAYOUT_TRACKS:
            raise ValueError(f"Column count must be <= {MAX_LAYOUT_TRACKS}")
        self.node.content["layout"] = "columns"
        self.node.content["column_count"] = count
        if gap is not None:
            self.node.content["gap"] = _edge_points(gap)
        return self

    def keep_together(self: BuilderT, value: bool = True) -> BuilderT:
        """Ask pagination to keep this node together when possible."""

        self.node.content["keep_together"] = value
        return self

    def keep_with_next(self: BuilderT, value: bool = True) -> BuilderT:
        """Ask pagination to keep this node with the next flow sibling."""

        self.node.content["keep_with_next"] = value
        return self

    def page_break_before(self: BuilderT, value: bool = True) -> BuilderT:
        """Force a page break before this node when paginating."""

        self.node.content["page_break_before"] = value
        return self

    def page_break_after(self: BuilderT, value: bool = True) -> BuilderT:
        """Force a page break after this node when paginating."""

        self.node.content["page_break_after"] = value
        return self

    def build(self) -> LayoutNode:
        """Return the underlying layout node."""

        return self.node


class ContainerBuilder(NodeBuilder):
    """Base class for builders that can contain child nodes."""

    def add(self: ContainerT, child: NodeBuilder) -> ContainerT:
        """Add an existing builder as a child and return this container."""

        _ = self.node.add_child(child.build())
        return self

    def add_text(self, text: str) -> "Text":
        """Create and add a ``Text`` child, returning the child builder."""

        from .elements.text import Text

        child = Text(text)
        _ = self.add(cast(NodeBuilder, child))
        return child

    def add_rich_text(self, text: str = "") -> "RichText":
        """Create and add a ``RichText`` child, returning the child builder."""

        from .elements.rich_text import RichText

        child = RichText(text)
        _ = self.add(cast(NodeBuilder, child))
        return child

    def add_image(self, src: str | bytes | PathLike[str]) -> "Image":
        """Create and add an ``Image`` child.

        ``src`` may be a string path, ``pathlib.Path``, image bytes, or a
        ``data:image/...;base64,...`` string.
        """

        from .elements.image import Image

        child = Image(src)
        _ = self.add(child)
        return child

    def add_rect(self, text: str | None = None) -> "Rect":
        """Create and add a rectangle shape child, optionally with label text."""

        from .elements.shape import Rect

        child = Rect(text)
        _ = self.add(child)
        return child

    def add_line(self) -> "Line":
        """Create and add a line shape child."""

        from .elements.shape import Line

        child = Line()
        _ = self.add(child)
        return child

    def add_spacer(self, height: SizeInput) -> "Spacer":
        """Create and add a fixed-height spacer child."""

        from .elements.spacer import Spacer

        child = Spacer(height)
        _ = self.add(child)
        return child

    def add_canvas(self) -> "Canvas":
        """Create and add a nested ``Canvas`` layer container."""

        from .containers.canvas import Canvas

        child = Canvas()
        _ = self.add(child)
        return child

    def add_frame(self) -> "Frame":
        """Create and add a nested flow ``Frame`` container."""

        from .containers.frame import Frame

        child = Frame()
        _ = self.add(cast(NodeBuilder, child))
        return child

    def add_table(self, rows: Sequence[Sequence[object]]) -> "Table":
        """Create and add a ``Table`` child from row data."""

        from .containers.table import Table

        child = Table(rows)
        _ = self.add(child)
        return child


class PageBuilder(ContainerBuilder):
    """Single PDF page builder returned by ``document().page(...)``."""

    def __init__(self, size: str | tuple[float, float] = "A4") -> None:
        """Create a page with a named or explicit ``(width, height)`` size."""

        width, height = resolve_page_size(size)
        style = Style(width=Fixed(width), height=Fixed(height))
        super().__init__(LayoutNode(node_type="page", style=style))


def resolve_page_size(size: str | tuple[float, float]) -> tuple[float, float]:
    """Resolve ``"A4"``, ``"LETTER"``, or explicit page size tuples."""

    if isinstance(size, tuple):
        width, height = size
        if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0:
            raise ValueError("Page size must contain positive finite width and height")
        return size

    normalized = size.upper()
    try:
        return PAGE_SIZES[normalized]
    except KeyError as error:
        raise ValueError(f"Unsupported page size: {size}") from error
