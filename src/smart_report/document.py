"""Built documents, sections and repeating page overlays."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from math import isfinite
from typing import Literal, Protocol

from .layout.node import Edges, LayoutNode
from .style.units import Fixed, SizeSpec

DocumentMetadata = dict[str, str]
SaveTarget = str | BytesIO


class ResolveSizeFnProto(Protocol):
    def __call__(self, value: SizeSpec, reference: float | None, auto_value: float = 0.0) -> float: ...


class CloneNodeFnProto(Protocol):
    def __call__(self, node: LayoutNode, include_children: bool = True) -> LayoutNode: ...


@dataclass(slots=True)
class DocumentSection:
    """Internal section metadata used for scoped overlays and outlines."""

    section_id: str
    name: str | None
    page_numbering: Literal["continue", "restart"]
    outline: bool
    pages: list[LayoutNode]
    overlay_templates: dict[str, list[LayoutNode]]
    suppressed_overlays: set[str]


@dataclass(slots=True)
class Document:
    """Built document that can be saved to disk or rendered to bytes."""

    pages: list[LayoutNode]
    overlay_templates: dict[str, list[LayoutNode]] | None = None
    sections: list[DocumentSection] | None = None
    metadata: DocumentMetadata | None = None

    def save(self, file_path: str, *, debug_layout: bool = False) -> None:
        """Render and save this document to a PDF file path."""

        self._save_to_target(file_path, debug_layout=debug_layout)

    def save_to_bytes(self, *, debug_layout: bool = False) -> bytes:
        """Render this document and return raw PDF bytes."""

        buffer = BytesIO()
        self._save_to_target(buffer, debug_layout=debug_layout)
        return buffer.getvalue()

    def _save_to_target(self, target: SaveTarget, *, debug_layout: bool = False) -> None:
        from .render.document import save_document

        save_document(self, target, debug_layout=debug_layout)

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
                overlay.style.width = Fixed(resolve_size_fn(template.style.width, page.resolved_width, page.content_width))
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
        overlay.style.left = Fixed(resolve_size_fn(overlay.style.left or Fixed(0), page.resolved_width, 0.0) - page.style.padding.left)
        if overlay_kind == "header":
            overlay.style.top = Fixed(-page.style.padding.top)
            return
        if overlay_kind == "footer":
            footer_top = max(0.0, page.resolved_height - overlay_height)
            overlay.style.top = Fixed(footer_top - page.style.padding.top)
            return
        if overlay_kind == "watermark" and overlay.style.top is None:
            watermark_top = max(0.0, (page.resolved_height - overlay_height) / 2.0)
            overlay.style.top = Fixed(watermark_top - page.style.padding.top)
        elif overlay.style.top is not None:
            overlay.style.top = Fixed(resolve_size_fn(overlay.style.top, page.resolved_height, 0.0) - page.style.padding.top)


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


__all__ = ["Document"]
