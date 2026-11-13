"""Section-scoped page and overlay builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .document import DocumentSection

if TYPE_CHECKING:
    from ._builder_core import PageBuilder
    from .document_builder import DocumentBuilder
    from .containers.canvas import Canvas


class SectionBuilder:
    """Builder for a named document section."""

    def __init__(self, document: "DocumentBuilder", section: DocumentSection) -> None:
        self._document = document
        self.section = section

    def page(self, size: str | tuple[float, float] = "A4") -> PageBuilder:
        """Create a page inside this section."""

        return self._document._add_page_to_section(self.section, size)

    def header(self) -> "Canvas":
        """Create a section-scoped repeating header canvas."""

        return self._overlay("header", "__doc_header__", 200)

    def footer(self) -> "Canvas":
        """Create a section-scoped repeating footer canvas."""

        return self._overlay("footer", "__doc_footer__", 210)

    def watermark(self) -> "Canvas":
        """Create a section-scoped repeating watermark canvas."""

        return self._overlay("watermark", "__doc_watermark__", -100)

    def suppress_header(self) -> "SectionBuilder":
        """Disable inherited document headers for this section."""

        self.section.suppressed_overlays.add("header")
        return self

    def suppress_footer(self) -> "SectionBuilder":
        """Disable inherited document footers for this section."""

        self.section.suppressed_overlays.add("footer")
        return self

    def suppress_watermark(self) -> "SectionBuilder":
        """Disable inherited document watermarks for this section."""

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
