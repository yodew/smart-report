"""Document layout and rendering orchestration."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from ..document import _propagate_page_context, _propagate_section_page_context
from ..layout.node import Edges, LayoutNode
from ..style.units import resolve_size

if TYPE_CHECKING:
    from ..document import Document


def save_document(doc: Document, target: str | BytesIO, *, debug_layout: bool = False) -> None:
    """Run layout, pagination and painting using the registered runtime modules."""
    from ..layout import node, paginate, pass2_widths, pass3_heights, pass4_render
    from . import painters, rl_adapter

    if not doc.pages:
        raise ValueError("Document has no pages")

    first_page_size = doc._page_size(doc.pages[0], resolve_size)
    adapter = rl_adapter.ReportLabCanvasAdapter(target=target, page_size=first_page_size)
    if doc.metadata is not None:
        adapter.set_metadata(
            title=doc.metadata.get("title"),
            author=doc.metadata.get("author"),
            subject=doc.metadata.get("subject"),
            keywords=doc.metadata.get("keywords"),
        )

    rendered_pages: list[LayoutNode] = []
    for page in doc.pages:
        page_size = doc._page_size(page, resolve_size)
        section = doc._section_for_page(page)
        reserved_top, reserved_bottom = doc._reserved_overlay_space(section, page_size[1], resolve_size)
        base_padding = doc._base_page_padding(page)
        page.style.padding = Edges(
            top=max(base_padding.top, reserved_top),
            right=base_padding.right,
            bottom=max(base_padding.bottom, reserved_bottom),
            left=base_padding.left,
        )
        pass2_widths.resolve_widths(page, page_size[0])
        pass3_heights.resolve_heights(page, page_size[1])
        rendered_pages.extend(paginate.paginate_page(page))

    total_pages = len(rendered_pages)
    section_contexts = doc._section_page_contexts(rendered_pages)
    outlined_section_ids: set[str] = set()

    for index, page in enumerate(rendered_pages):
        page.page_index = index
        _propagate_page_context(page, page.page_index, total_pages)
        _propagate_section_page_context(page, section_contexts.get(id(page)))
        doc._apply_overlays(page, total_pages, section_contexts.get(id(page)), node.clone_layout_node, resolve_size)
        page_size = doc._page_size(page, resolve_size)
        adapter.set_page_size(page_size)

        pass2_widths.resolve_widths(page, page_size[0])
        pass3_heights.resolve_heights(page, page_size[1])

        section = doc._section_for_page(page)
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

        render_items = pass4_render.build_render_list(page)
        for item in render_items:
            painters.paint_render_item(adapter, item)

        if debug_layout:
            from .diagnostics import paint_layout_diagnostics

            paint_layout_diagnostics(adapter, page, render_items)

        if index < total_pages - 1:
            adapter.show_page()

    adapter.save()
