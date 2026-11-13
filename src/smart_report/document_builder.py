"""Mutable document builder and document factory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from .document import Document, DocumentMetadata, DocumentSection
from .layout.node import LayoutNode, Style
from .section import SectionBuilder

if TYPE_CHECKING:
    from ._builder_core import PageBuilder
    from .containers.canvas import Canvas


class DocumentBuilder:
    """Top-level chainable document builder."""

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
        """Built page nodes currently attached to the document."""

        return self._root.children

    def page(self, size: str | tuple[float, float] = "A4") -> PageBuilder:
        """Create a page in the default section.

        ``size`` accepts ``"A4"``, ``"LETTER"``, or an explicit
        ``(width, height)`` tuple in points.
        """

        return self._add_page_to_section(self._get_default_section(), size)

    def section(
        self,
        name: str | None = None,
        *,
        page_numbering: str = "restart",
        outline: bool = True,
    ) -> SectionBuilder:
        """Create a named document section.

        ``page_numbering`` accepts ``"restart"`` or ``"continue"``.
        Section headers, footers, watermarks, and page-number placeholders are
        scoped to pages added through the returned builder.
        """

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
        """Set PDF metadata fields and return this document builder."""

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
        """Build a ``Document`` ready to save or render to bytes."""

        return Document(
            pages=self.pages,
            overlay_templates={
                name: [node for node in nodes]
                for name, nodes in self._overlay_templates.items()
            },
            sections=[section for section in self._sections],
            metadata={name: value for name, value in self._metadata.items()},
        )

    def save(self, file_path: str, *, debug_layout: bool = False) -> None:
        """Build and save the document to a PDF file path."""

        self.build().save(file_path, debug_layout=debug_layout)

    def save_to_bytes(self, *, debug_layout: bool = False) -> bytes:
        """Build and render the document, returning raw PDF bytes."""

        return self.build().save_to_bytes(debug_layout=debug_layout)

    def header(self) -> "Canvas":
        """Create a repeating document-level header canvas."""

        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name("__doc_header__")
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(200)
        self._overlay_templates["header"].append(canvas.build())
        return canvas

    def footer(self) -> "Canvas":
        """Create a repeating document-level footer canvas."""

        from .containers.canvas import Canvas

        canvas = Canvas()
        canvas.name("__doc_footer__")
        canvas.absolute(0, 0)
        canvas.width("100%")
        canvas.z(210)
        self._overlay_templates["footer"].append(canvas.build())
        return canvas

    def watermark(self) -> "Canvas":
        """Create a repeating document-level watermark canvas."""

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
        from ._builder_core import PageBuilder

        page = PageBuilder(size)
        page.node.content["section_id"] = section.section_id
        section.pages.append(page.build())
        _ = self._root.add_child(page.build())
        return page


def document() -> DocumentBuilder:
    """Create a new chainable document builder."""

    return DocumentBuilder()
