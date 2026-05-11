"""Internal chainable builder API for smart-report."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from importlib import import_module
from math import isfinite
from typing import TYPE_CHECKING, Literal, Protocol, TypeVar, cast

from .layout.node import Edges, LayoutNode, OverflowMode, PositionMode, Style
from .style.color import parse_color
from .style.font import DEFAULT_FONT_REGISTRY
from .style.typography import normalize_text_direction, normalize_typography_mode
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
DocumentMetadata = dict[str, str]

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
        self.node.style.font_family = None
        return self

    def font_family(self: BuilderT, name: str) -> BuilderT:
        self.node.style.font_family = name
        self.node.style.font_name = DEFAULT_FONT_REGISTRY.font_name_for_family(name)
        return self

    def font_size(self: BuilderT, size: float) -> BuilderT:
        self.node.style.font_size = size
        if self.node.style.line_height < size:
            self.node.style.line_height = size * 1.2
        return self

    def line_height(self: BuilderT, value: float) -> BuilderT:
        self.node.style.line_height = value
        return self

    def typography(self: BuilderT, value: str) -> BuilderT:
        self.node.style.typography = normalize_typography_mode(value)
        return self

    def text_direction(self: BuilderT, value: str) -> BuilderT:
        self.node.style.text_direction = normalize_text_direction(value)
        return self


    def stroke(self: BuilderT, color: str | None, width: float) -> BuilderT:
        self.node.style.stroke_color = parse_color(color)
        self.node.style.stroke_width = width
        return self

    def radius(self: BuilderT, value: float) -> BuilderT:
        self.node.style.border_radius = value
        return self

    def layout(self: BuilderT, value: str) -> BuilderT:
        normalized = value.lower()
        if normalized not in {"flow", "flex", "grid", "columns"}:
            raise ValueError(f"Unsupported layout mode: {value}")
        self.node.content["layout"] = normalized
        return self

    def gap(self: BuilderT, value: SizeInput) -> BuilderT:
        self.node.content["gap"] = _edge_points(value)
        return self

    def flex(self: BuilderT, direction: str = "row", *, gap: SizeInput | None = None, wrap: bool = False) -> BuilderT:
        normalized = direction.lower()
        if normalized not in {"row", "column"}:
            raise ValueError(f"Unsupported flex direction: {direction}")
        if wrap:
            raise ValueError("Flex wrapping is not supported yet")
        self.node.content["layout"] = "flex"
        self.node.content["flex_direction"] = normalized
        if gap is not None:
            self.node.content["gap"] = _edge_points(gap)
        return self

    def grid(self: BuilderT, columns: int, *, gap: SizeInput | None = None) -> BuilderT:
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
        self.node.content["keep_together"] = value
        return self

    def keep_with_next(self: BuilderT, value: bool = True) -> BuilderT:
        self.node.content["keep_with_next"] = value
        return self

    def page_break_before(self: BuilderT, value: bool = True) -> BuilderT:
        self.node.content["page_break_before"] = value
        return self

    def page_break_after(self: BuilderT, value: bool = True) -> BuilderT:
        self.node.content["page_break_after"] = value
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
        _ = self.add(cast(NodeBuilder, child))
        return child

    def add_image(self, src: str | bytes) -> "Image":
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
        _ = self.add(cast(NodeBuilder, child))
        return child

    def add_table(self, rows: Sequence[Sequence[object]]) -> "Table":
        from .containers.table import Table

        child = Table(rows)
        _ = self.add(child)
        return child


class PageBuilder(ContainerBuilder):
    def __init__(self, size: str | tuple[float, float] = "A4") -> None:
        width, height = resolve_page_size(size)
        style = Style(width=Fixed(width), height=Fixed(height))
        super().__init__(LayoutNode(node_type="page", style=style))


@dataclass(slots=True)
class DocumentSection:
    section_id: str
    name: str | None
    page_numbering: Literal["continue", "restart"]
    outline: bool
    pages: list[LayoutNode]
    overlay_templates: dict[str, list[LayoutNode]]
    suppressed_overlays: set[str]


class SectionBuilder:
    def __init__(self, document: "DocumentBuilder", section: DocumentSection) -> None:
        self._document = document
        self.section = section

    def page(self, size: str | tuple[float, float] = "A4") -> PageBuilder:
        return self._document._add_page_to_section(self.section, size)

    def header(self) -> "Canvas":
        return self._overlay("header", "__doc_header__", 200)

    def footer(self) -> "Canvas":
        return self._overlay("footer", "__doc_footer__", 210)

    def watermark(self) -> "Canvas":
        return self._overlay("watermark", "__doc_watermark__", -100)

    def suppress_header(self) -> "SectionBuilder":
        self.section.suppressed_overlays.add("header")
        return self

    def suppress_footer(self) -> "SectionBuilder":
        self.section.suppressed_overlays.add("footer")
        return self

    def suppress_watermark(self) -> "SectionBuilder":
        self.section.suppressed_overlays.add("watermark")
        return self

    def _overlay(self, overlay_kind: str, name: str, z_index: int) -> "Canvas":
        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name(name)
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(z_index)
        self.section.overlay_templates[overlay_kind].append(canvas.build())
        return canvas


class DocumentBuilder:
    _root: LayoutNode

    def __init__(self) -> None:
        self._root = LayoutNode(node_type="document", style=Style())
        self._sections: list[DocumentSection] = []
        self._default_section: DocumentSection | None = None
        self._overlay_templates: dict[str, list[LayoutNode]] = {
            "header": [],
            "footer": [],
            "watermark": [],
        }
        self._metadata: DocumentMetadata = {}

    @property
    def pages(self) -> list[LayoutNode]:
        return self._root.children

    def page(self, size: str | tuple[float, float] = "A4") -> PageBuilder:
        return self._add_page_to_section(self._get_default_section(), size)

    def section(
        self,
        name: str | None = None,
        *,
        page_numbering: str = "restart",
        outline: bool = True,
    ) -> SectionBuilder:
        if page_numbering not in {"continue", "restart"}:
            raise ValueError(f"Unsupported section page numbering: {page_numbering}")
        section = self._create_section(
            name=name,
            page_numbering=cast(Literal["continue", "restart"], page_numbering),
            outline=outline,
        )
        return SectionBuilder(self, section)

    def metadata(
        self,
        title: str | None = None,
        author: str | None = None,
        subject: str | None = None,
        keywords: str | None = None,
    ) -> "DocumentBuilder":
        values = {
            "title": title,
            "author": author,
            "subject": subject,
            "keywords": keywords,
        }
        for name, value in values.items():
            if value is not None:
                self._metadata[name] = value
        return self

    def build(self) -> "Document":
        return Document(
            pages=self.pages,
            overlay_templates={
                name: [node for node in nodes]
                for name, nodes in self._overlay_templates.items()
            },
            sections=[section for section in self._sections],
            metadata={name: value for name, value in self._metadata.items()},
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

    def _get_default_section(self) -> DocumentSection:
        if self._default_section is None:
            self._default_section = self._create_section(
                name=None,
                page_numbering="continue",
                outline=False,
            )
        return self._default_section

    def _create_section(
        self,
        *,
        name: str | None,
        page_numbering: Literal["continue", "restart"],
        outline: bool,
    ) -> DocumentSection:
        section = DocumentSection(
            section_id=f"section-{len(self._sections) + 1}",
            name=name,
            page_numbering=page_numbering,
            outline=outline,
            pages=[],
            overlay_templates={
                "header": [],
                "footer": [],
                "watermark": [],
            },
            suppressed_overlays=set(),
        )
        self._sections.append(section)
        return section

    def _add_page_to_section(self, section: DocumentSection, size: str | tuple[float, float]) -> PageBuilder:
        page = PageBuilder(size)
        page.node.content["section_id"] = section.section_id
        section.pages.append(page.build())
        _ = self._root.add_child(page.build())
        return page


def resolve_page_size(size: str | tuple[float, float]) -> tuple[float, float]:
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


def document() -> DocumentBuilder:
    return DocumentBuilder()


@dataclass(slots=True)
class Document:
    pages: list[LayoutNode]
    overlay_templates: dict[str, list[LayoutNode]] | None = None
    sections: list[DocumentSection] | None = None
    metadata: DocumentMetadata | None = None

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
        if self.metadata is not None:
            adapter.set_metadata(
                title=self.metadata.get("title"),
                author=self.metadata.get("author"),
                subject=self.metadata.get("subject"),
                keywords=self.metadata.get("keywords"),
            )

        rendered_pages: list[LayoutNode] = []
        for page in self.pages:
            page_size = self._page_size(page, resolve_size_fn)
            section = self._section_for_page(page)
            reserved_top, reserved_bottom = self._reserved_overlay_space(section, page_size[1], resolve_size_fn)
            base_padding = self._base_page_padding(page)
            page.style.padding = Edges(
                top=max(base_padding.top, reserved_top),
                right=base_padding.right,
                bottom=max(base_padding.bottom, reserved_bottom),
                left=base_padding.left,
            )
            resolve_widths_fn(page, page_size[0])
            resolve_heights_fn(page, page_size[1])
            rendered_pages.extend(paginate_page_fn(page))

        total_pages = len(rendered_pages)
        section_contexts = self._section_page_contexts(rendered_pages)
        outlined_section_ids: set[str] = set()

        for index, page in enumerate(rendered_pages):
            page.page_index = index
            _propagate_page_context(page, page.page_index, total_pages)
            _propagate_section_page_context(page, section_contexts.get(id(page)))
            self._apply_overlays(page, total_pages, section_contexts.get(id(page)), clone_layout_node_fn, resolve_size_fn)
            page_size = self._page_size(page, resolve_size_fn)
            adapter.set_page_size(page_size)

            resolve_widths_fn(page, page_size[0])
            resolve_heights_fn(page, page_size[1])

            section = self._section_for_page(page)
            if (
                section is not None
                and section.outline
                and section.name
                and section.section_id not in outlined_section_ids
            ):
                key = f"section-{section.section_id}"
                adapter.bookmark_page(key)
                adapter.add_outline_entry(section.name, key, level=0)
                outlined_section_ids.add(section.section_id)

            for item in build_render_list_fn(page):
                paint_render_item_fn(adapter, item)

            if index < total_pages - 1:
                adapter.show_page()

        adapter.save()

    def _page_size(self, page: LayoutNode, resolve_size_fn: ResolveSizeFnProto) -> tuple[float, float]:
        width = float(resolve_size_fn(page.style.width, None, 0.0))
        height = float(resolve_size_fn(page.style.height, None, 0.0))
        if not isfinite(width) or not isfinite(height) or width <= 0 or height <= 0:
            raise ValueError("Page size must contain positive finite width and height")
        return (width, height)

    def _base_page_padding(self, page: LayoutNode) -> Edges:
        value = page.content.get("base_padding")
        if isinstance(value, Edges):
            return value
        base_padding = Edges(
            top=page.style.padding.top,
            right=page.style.padding.right,
            bottom=page.style.padding.bottom,
            left=page.style.padding.left,
        )
        page.content["base_padding"] = base_padding
        return base_padding

    def _section_for_page(self, page: LayoutNode) -> DocumentSection | None:
        section_id = page.content.get("section_id")
        if not isinstance(section_id, str) or not self.sections:
            return None
        for section in self.sections:
            if section.section_id == section_id:
                return section
        return None

    def _resolved_overlay_templates(self, section: DocumentSection | None, overlay_kind: str) -> list[LayoutNode]:
        if section is not None and overlay_kind in section.suppressed_overlays:
            return []
        if section is not None:
            section_templates = section.overlay_templates.get(overlay_kind, [])
            if section_templates:
                return section_templates
        if self.overlay_templates is None:
            return []
        return self.overlay_templates.get(overlay_kind, [])

    def _apply_overlays(
        self,
        page: LayoutNode,
        total_pages: int,
        section_context: dict[str, object] | None,
        clone_node_fn: CloneNodeFnProto,
        resolve_size_fn: ResolveSizeFnProto,
    ) -> None:
        page.remove_children_by_name("__doc_header__")
        page.remove_children_by_name("__doc_footer__")
        page.remove_children_by_name("__doc_watermark__")

        section = self._section_for_page(page)
        for overlay_kind in ("watermark", "header", "footer"):
            for template in self._resolved_overlay_templates(section, overlay_kind):
                overlay = clone_node_fn(template)
                self._anchor_overlay(overlay_kind, overlay, page, resolve_size_fn)
                _propagate_page_context(overlay, page.page_index, total_pages)
                _propagate_section_page_context(overlay, section_context)
                _ = page.add_child(overlay)

    def _section_page_contexts(self, rendered_pages: list[LayoutNode]) -> dict[int, dict[str, object]]:
        contexts: dict[int, dict[str, object]] = {}
        groups: list[list[tuple[LayoutNode, DocumentSection | None]]] = []
        current_group: list[tuple[LayoutNode, DocumentSection | None]] = []
        has_group = False
        previous_section_id: str | None = None

        for page in rendered_pages:
            section = self._section_for_page(page)
            section_id = section.section_id if section is not None else None
            begins_section = section_id != previous_section_id
            starts_group = (
                not has_group
                or section is None
                or (begins_section and section.page_numbering == "restart")
            )
            if starts_group:
                current_group = []
                groups.append(current_group)
                has_group = True
            current_group.append((page, section))
            previous_section_id = section_id

        for group in groups:
            total = len(group)
            for offset, (page, section) in enumerate(group, start=1):
                contexts[id(page)] = {
                    "section_name": "" if section is None or section.name is None else section.name,
                    "section_page_number": offset,
                    "section_total_pages": total,
                }
        return contexts

    def _reserved_overlay_space(
        self,
        section: DocumentSection | None,
        page_height: float,
        resolve_size_fn: ResolveSizeFnProto,
    ) -> tuple[float, float]:
        header_heights = [
            float(resolve_size_fn(template.style.height, page_height, 0.0))
            for template in self._resolved_overlay_templates(section, "header")
        ]
        footer_heights = [
            float(resolve_size_fn(template.style.height, page_height, 0.0))
            for template in self._resolved_overlay_templates(section, "footer")
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


def _propagate_section_page_context(node: LayoutNode, section_context: dict[str, object] | None) -> None:
    if section_context is not None:
        node.content.update(section_context)
    for child in node.children:
        _propagate_section_page_context(child, section_context)
