"""Pass 4: flatten laid out nodes into render items."""

from __future__ import annotations

from .node import LayoutNode, Rect, RenderItem


def build_render_list(root: LayoutNode) -> list[RenderItem]:
    render_items: list[RenderItem] = []
    _flatten_node(
        node=root,
        parent_abs_x=0.0,
        parent_abs_y=0.0,
        stacking_path=(),
        tree_order_seed=[0],
        clip_stack=(),
        render_items=render_items,
    )
    render_items.sort(key=lambda item: item.sort_key)
    return render_items


def _flatten_node(
    node: LayoutNode,
    parent_abs_x: float,
    parent_abs_y: float,
    stacking_path: tuple[int, ...],
    tree_order_seed: list[int],
    clip_stack: tuple[Rect, ...],
    render_items: list[RenderItem],
) -> None:
    abs_x = parent_abs_x + node.local_x
    abs_y = parent_abs_y + node.local_y

    tree_order = tree_order_seed[0]
    tree_order_seed[0] += 1

    context_path = stacking_path
    if node.creates_stacking_context:
        context_path = stacking_path + (node.style.z_index, tree_order)

    sort_key = context_path if node.creates_stacking_context else context_path + (node.style.z_index, tree_order)
    active_clips = clip_stack
    if node.style.overflow.value == "hidden":
        active_clips = clip_stack + (
            Rect(abs_x, abs_y, node.resolved_width, node.resolved_height),
        )

    if node.is_renderable:
        render_items.append(
            RenderItem(
                node=node,
                absolute_bounds=Rect(abs_x, abs_y, node.resolved_width, node.resolved_height),
                clip_rects=active_clips,
                sort_key=sort_key,
            )
        )

    for child in node.children:
        _flatten_node(
            node=child,
            parent_abs_x=abs_x,
            parent_abs_y=abs_y,
            stacking_path=context_path,
            tree_order_seed=tree_order_seed,
            clip_stack=active_clips,
            render_items=render_items,
        )
