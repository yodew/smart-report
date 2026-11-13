"""Page-level flow pagination; frame splitting lives in paginate.py."""

from __future__ import annotations

from typing import Final

from .node import LayoutNode, clone_layout_node

STARTS_ON_FOLLOWING_PAGE: Final = "_starts_on_following_page"


def _flag(node: LayoutNode, key: str) -> bool:
    return bool(node.content.get(key, False))


def paginate_page(page: LayoutNode) -> list[LayoutNode]:
    max_page_height = page.resolved_height
    current_page = _clone_page_shell(page)
    paginated_pages: list[LayoutNode] = [current_page]

    for child in page.children:
        if child.style.position.value == "absolute":
            _ = current_page.add_child(clone_layout_node(child))
            continue

        if _flag(child, "page_break_before") and current_page.children:
            current_page = _new_generated_page(page, paginated_pages)

        current_page = _append_with_pagination(
            current_page=current_page,
            source_page=page,
            child=child,
            output_pages=paginated_pages,
            max_page_height=max_page_height,
        )
        if _flag(child, "page_break_after"):
            current_page = _new_generated_page(page, paginated_pages)

    return [page_slice for page_slice in paginated_pages if page_slice.children]


def _append_with_pagination(
    current_page: LayoutNode,
    source_page: LayoutNode,
    child: LayoutNode,
    output_pages: list[LayoutNode],
    max_page_height: float,
) -> LayoutNode:
    content_bottom = max(1.0, max_page_height - current_page.style.padding.bottom)
    if child.local_y + child.resolved_height <= content_bottom:
        _ = current_page.add_child(clone_layout_node(child))
        return current_page

    if _flag(child, "keep_together"):
        current_page = _new_generated_page(source_page, output_pages)
        _ = current_page.add_child(clone_layout_node(child))
        return current_page

    if child.node_type == "frame":
        remaining_height = max(1.0, content_bottom - _current_page_flow_extent(current_page))
        from .paginate import split_frame_node

        following_height = max(1.0, max_page_height - source_page.style.padding.vertical)
        frame_slices = split_frame_node(child, remaining_height, following_height)
        if not frame_slices:
            _ = current_page.add_child(clone_layout_node(child))
            return current_page

        first_slice = True
        for frame_slice in frame_slices:
            if first_slice:
                if bool(frame_slice.content.pop(STARTS_ON_FOLLOWING_PAGE, False)):
                    current_page = _new_generated_page(source_page, output_pages)
                _ = current_page.add_child(frame_slice)
                first_slice = False
                continue
            current_page = _new_generated_page(source_page, output_pages)
            _ = current_page.add_child(frame_slice)
        return current_page

    current_page = _new_generated_page(source_page, output_pages)
    _ = current_page.add_child(clone_layout_node(child))
    return current_page


def _current_page_flow_extent(page: LayoutNode) -> float:
    if not page.children:
        return page.style.padding.top
    return max(
        (
            child.local_y
            + child.resolved_height
            + child.style.margin.bottom
            for child in page.children
            if child.style.position.value == "flow"
        ),
        default=page.style.padding.top,
    )


def _clone_page_shell(page: LayoutNode) -> LayoutNode:
    clone = clone_layout_node(page, include_children=False)
    clone.children = []
    return clone


def _new_generated_page(source_page: LayoutNode, output_pages: list[LayoutNode]) -> LayoutNode:
    new_page = _clone_page_shell(source_page)
    output_pages.append(new_page)
    return new_page
