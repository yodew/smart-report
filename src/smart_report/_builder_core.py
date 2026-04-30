"""Internal chainable builder API for smart-report."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from .layout.node import Edges, LayoutNode, OverflowMode, PositionMode, Style
from .style.color import parse_color
from .style.units import Fixed, SizeInput, parse_size

if TYPE_CHECKING:
    from .render.rl_adapter import ReportLabCanvasAdapter
    from .containers.canvas import Canvas
    from .containers.frame import Frame
    from .containers.table import Table
    from .elements.image import Image
    from .elements.shape import Line, Rect
    from .elements.spacer import Spacer
    from .elements.text import Text


class ResolveSizeFnProto(Protocol):
    def __call__(self, value: object, reference: float | None, auto_value: float = 0.0) -> float: ...


class ResolveWidthsFnProto(Protocol):
    def __call__(self, root: LayoutNode, available_width: float | None = None) -> None: ...


class ResolveHeightsFnProto(Protocol):
    def __call__(self, root: LayoutNode, available_height: float | None = None) -> None: ...


class BuildRenderListFnProto(Protocol):
    def __call__(self, root: LayoutNode) -> list[object]: ...


class PaginatePageFnProto(Protocol):
    def __call__(self, page: LayoutNode) -> list[LayoutNode]: ...


class PaintRenderItemFnProto(Protocol):
    def __call__(self, adapter: object, item: object) -> None: ...


class CloneNodeFnProto(Protocol):
    def __call__(self, node: LayoutNode, include_children: bool = True) -> LayoutNode: ...


class AdapterCtorProto(Protocol):
    def __call__(self, file_path: str, page_size: tuple[float, float]) -> "ReportLabCanvasAdapter": ...

BuilderT = TypeVar("BuilderT", bound="NodeBuilder")
ContainerT = TypeVar("ContainerT", bound="ContainerBuilder")
EdgeInput = SizeInput | tuple[SizeInput, ...]

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (595.2756, 841.8898),
    "LETTER": (612.0, 792.0),
}


def _edge_points(value: SizeInput) -> float:
    parsed = parse_size(value)
    if not isinstance(parsed, Fixed):
        raise ValueError("Padding and margin require fixed point-compatible values")
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


class NodeBuilder:
    node: LayoutNode

    def __init__(self, node: LayoutNode) -> None:
        self.node = node

    def name(self: BuilderT, value: str) -> BuilderT:
        self.node.name = value
        return self

    def width(self: BuilderT, value: SizeInput) -> BuilderT:
        self.node.style.width = parse_size(value)
        return self

    def height(self: BuilderT, value: SizeInput) -> BuilderT:
        self.node.style.height = parse_size(value)
        return self

    def size(self: BuilderT, width: SizeInput, height: SizeInput) -> BuilderT:
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
        self.node.style.background = parse_color(value)
        return self

    def color(self: BuilderT, value: str | None) -> BuilderT:
        self.node.style.color = parse_color(value)
        return self

    def opacity(self: BuilderT, value: float) -> BuilderT:
        self.node.style.opacity = value
        return self

    def z(self: BuilderT, value: int) -> BuilderT:
        self.node.style.z_index = value
        return self

    def overflow(self: BuilderT, value: str) -> BuilderT:
        self.node.style.overflow = OverflowMode(value)
        return self

    def absolute(self: BuilderT, left: SizeInput = 0, top: SizeInput = 0) -> BuilderT:
        self.node.style.position = PositionMode.ABSOLUTE
        self.node.style.left = parse_size(left)
        self.node.style.top = parse_size(top)
        return self

    def flow(self: BuilderT) -> BuilderT:
        self.node.style.position = PositionMode.FLOW
        self.node.style.left = None
        self.node.style.top = None
        return self

    def font(self: BuilderT, name: str) -> BuilderT:
        self.node.style.font_name = name
        return self

    def font_size(self: BuilderT, size: float) -> BuilderT:
        self.node.style.font_size = size
        if self.node.style.line_height < size:
            self.node.style.line_height = size * 1.2
        return self

    def line_height(self: BuilderT, value: float) -> BuilderT:
        self.node.style.line_height = value
        return self

    def stroke(self: BuilderT, color: str | None, width: float) -> BuilderT:
        self.node.style.stroke_color = parse_color(color)
        self.node.style.stroke_width = width
        return self

    def radius(self: BuilderT, value: float) -> BuilderT:
        self.node.style.border_radius = value
        return self

    def build(self) -> LayoutNode:
        return self.node


class ContainerBuilder(NodeBuilder):
    def add(self: ContainerT, child: NodeBuilder) -> ContainerT:
        _ = self.node.add_child(child.build())
        return self

    def add_text(self, text: str) -> "Text":
        from .elements.text import Text

        child = Text(text)
        _ = self.add(child)
        return child

    def add_image(self, src: str) -> "Image":
        from .elements.image import Image

        child = Image(src)
        _ = self.add(child)
        return child

    def add_rect(self) -> "Rect":
        from .elements.shape import Rect

        child = Rect()
        _ = self.add(child)
        return child

    def add_line(self) -> "Line":
        from .elements.shape import Line

        child = Line()
        _ = self.add(child)
        return child

    def add_spacer(self, height: SizeInput) -> "Spacer":
        from .elements.spacer import Spacer

        child = Spacer(height)
        _ = self.add(child)
        return child

    def add_canvas(self) -> "Canvas":
        from .containers.canvas import Canvas

        child = Canvas()
        _ = self.add(child)
        return child

    def add_frame(self) -> "Frame":
        from .containers.frame import Frame

        child = Frame()
        _ = self.add(child)
        return child

    def add_table(self, rows: list[list[str]]) -> "Table":
        from .containers.table import Table

        child = Table(rows)
        _ = self.add(child)
        return child


class PageBuilder(ContainerBuilder):
    def __init__(self, size: str | tuple[float, float] = "A4") -> None:
        width, height = resolve_page_size(size)
        style = Style(width=Fixed(width), height=Fixed(height))
        super().__init__(LayoutNode(node_type="page", style=style))


class DocumentBuilder:
    _root: LayoutNode

    def __init__(self) -> None:
        self._root = LayoutNode(node_type="document", style=Style())
        self._overlay_templates: dict[str, list[LayoutNode]] = {
            "header": [],
            "footer": [],
            "watermark": [],
        }

    @property
    def pages(self) -> list[LayoutNode]:
        return self._root.children

    def page(self, size: str | tuple[float, float] = "A4") -> PageBuilder:
        page = PageBuilder(size)
        _ = self._root.add_child(page.build())
        return page

    def build(self) -> "Document":
        return Document(
            pages=self.pages,
            overlay_templates={
                name: [node for node in nodes]
                for name, nodes in self._overlay_templates.items()
            },
        )

    def save(self, file_path: str) -> None:
        self.build().save(file_path)

    def header(self) -> "Canvas":
        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name("__doc_header__")
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(200)
        self._overlay_templates["header"].append(canvas.build())
        return canvas

    def footer(self) -> "Canvas":
        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name("__doc_footer__")
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(210)
        self._overlay_templates["footer"].append(canvas.build())
        return canvas

    def watermark(self) -> "Canvas":
        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name("__doc_watermark__")
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(-100)
        self._overlay_templates["watermark"].append(canvas.build())
        return canvas


def resolve_page_size(size: str | tuple[float, float]) -> tuple[float, float]:
    if isinstance(size, tuple):
        return size

    normalized = size.upper()
    try:
        return PAGE_SIZES[normalized]
    except KeyError as error:
        raise ValueError(f"Unsupported page size: {size}") from error


def document() -> DocumentBuilder:
    return DocumentBuilder()


@dataclass(slots=True)
class Document:
    pages: list[LayoutNode]
    overlay_templates: dict[str, list[LayoutNode]] | None = None

    def save(self, file_path: str) -> None:
        if not self.pages:
            raise ValueError("Document has no pages")

        pass2_module = import_module("smart_report.layout.pass2_widths")
        pass3_module = import_module("smart_report.layout.pass3_heights")
        pass4_module = import_module("smart_report.layout.pass4_render")
        paginate_module = import_module("smart_report.layout.paginate")
        node_module = import_module("smart_report.layout.node")
        painters_module = import_module("smart_report.render.painters")
        adapter_module = import_module("smart_report.render.rl_adapter")
        units_module = import_module("smart_report.style.units")

        resolve_widths_fn = cast(ResolveWidthsFnProto, getattr(pass2_module, "resolve_widths"))
        resolve_heights_fn = cast(ResolveHeightsFnProto, getattr(pass3_module, "resolve_heights"))
        build_render_list_fn = cast(BuildRenderListFnProto, getattr(pass4_module, "build_render_list"))
        paginate_page_fn = cast(PaginatePageFnProto, getattr(paginate_module, "paginate_page"))
        clone_layout_node_fn = cast(CloneNodeFnProto, getattr(node_module, "clone_layout_node"))
        paint_render_item_fn = cast(PaintRenderItemFnProto, getattr(painters_module, "paint_render_item"))
        reportlab_canvas_adapter = cast(AdapterCtorProto, getattr(adapter_module, "ReportLabCanvasAdapter"))
        resolve_size_fn = cast(ResolveSizeFnProto, getattr(units_module, "resolve_size"))

        first_page_size = self._page_size(self.pages[0], resolve_size_fn)
        adapter = reportlab_canvas_adapter(file_path=file_path, page_size=first_page_size)

        rendered_pages: list[LayoutNode] = []
        for page in self.pages:
            page_size = self._page_size(page, resolve_size_fn)
            reserved_top, reserved_bottom = self._reserved_overlay_space(page_size[1], resolve_size_fn)
            page.style.padding = Edges(
                top=max(page.style.padding.top, reserved_top),
                right=page.style.padding.right,
                bottom=max(page.style.padding.bottom, reserved_bottom),
                left=page.style.padding.left,
            )
            resolve_widths_fn(page, page_size[0])
            resolve_heights_fn(page, page_size[1])
            rendered_pages.extend(paginate_page_fn(page))

        total_pages = len(rendered_pages)

        for index, page in enumerate(rendered_pages):
            page.page_index = index
            _propagate_page_context(page, page.page_index, total_pages)
            self._apply_overlays(page, total_pages, clone_layout_node_fn, resolve_size_fn)
            page_size = self._page_size(page, resolve_size_fn)
            adapter.set_page_size(page_size)

            resolve_widths_fn(page, page_size[0])
            resolve_heights_fn(page, page_size[1])

            for item in build_render_list_fn(page):
                paint_render_item_fn(adapter, item)

            if index < total_pages - 1:
                adapter.show_page()

        adapter.save()

    def _page_size(self, page: LayoutNode, resolve_size_fn: ResolveSizeFnProto) -> tuple[float, float]:
        width = float(resolve_size_fn(page.style.width, None, 0.0))
        height = float(resolve_size_fn(page.style.height, None, 0.0))
        return (width, height)

    def _apply_overlays(
        self,
        page: LayoutNode,
        total_pages: int,
        clone_node_fn: CloneNodeFnProto,
        resolve_size_fn: ResolveSizeFnProto,
    ) -> None:
        if not self.overlay_templates:
            return

        page.remove_children_by_name("__doc_header__")
        page.remove_children_by_name("__doc_footer__")
        page.remove_children_by_name("__doc_watermark__")

        for overlay_kind in ("watermark", "header", "footer"):
            for template in self.overlay_templates.get(overlay_kind, []):
                overlay = clone_node_fn(template)
                self._anchor_overlay(overlay_kind, overlay, page, resolve_size_fn)
                _propagate_page_context(overlay, page.page_index, total_pages)
                _ = page.add_child(overlay)

    def _reserved_overlay_space(self, page_height: float, resolve_size_fn: ResolveSizeFnProto) -> tuple[float, float]:
        templates = self.overlay_templates or {}
        header_heights = [
            float(resolve_size_fn(template.style.height, page_height, 0.0))
            for template in templates.get("header", [])
        ]
        footer_heights = [
            float(resolve_size_fn(template.style.height, page_height, 0.0))
            for template in templates.get("footer", [])
        ]
        return (sum(header_heights), sum(footer_heights))

    def _anchor_overlay(
        self,
        overlay_kind: str,
        overlay: LayoutNode,
        page: LayoutNode,
        resolve_size_fn: ResolveSizeFnProto,
    ) -> None:
        overlay_height = float(resolve_size_fn(overlay.style.height, page.resolved_height, 0.0))
        if overlay_kind == "header":
            overlay.style.top = Fixed(0.0)
            return
        if overlay_kind == "footer":
            footer_top = max(0.0, page.resolved_height - overlay_height)
            overlay.style.top = Fixed(footer_top)
            return
        if overlay_kind == "watermark" and overlay.style.top is None:
            watermark_top = max(0.0, (page.resolved_height - overlay_height) / 2.0)
            overlay.style.top = Fixed(watermark_top)


def _propagate_page_context(node: LayoutNode, page_index: int, total_pages: int) -> None:
    node.page_index = page_index
    node.content["total_pages"] = total_pages
    for child in node.children:
        _propagate_page_context(child, page_index, total_pages)
