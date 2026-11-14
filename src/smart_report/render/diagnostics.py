"""Opt-in PDF layout overlays, drawn after normal content without changing layout."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Final

from ..layout.node import LayoutNode, PositionMode, Rect, RenderItem
from ..style.color import RGBA
from .rl_adapter import ReportLabCanvasAdapter

BOUNDS_COLOR: Final = RGBA(0.1, 0.35, 0.9, 0.85)
CONTENT_COLOR: Final = RGBA(0.0, 0.6, 0.3, 0.85)
CLIP_COLOR: Final = RGBA(1.0, 0.45, 0.0, 0.9)


class LayoutOverflowWarning(UserWarning):
    """A named node extends beyond the physical page or flow body in debug mode."""

    def __init__(self, page_number: int, item: RenderItem, body_bounds: Rect | None = None) -> None:
        self.page_number = page_number
        self.node_name = item.node.name or item.node.node_type
        self.bounds = item.absolute_bounds
        self.body_bounds = body_bounds
        boundary = "the physical page" if body_bounds is None else f"the page body {body_bounds} (padding excluded)"
        super().__init__(
            f"Page {page_number}: {self.node_name!r} ({item.node.node_type}) "
            f"bounds={self.bounds} exceed {boundary}. "
            "Reduce the node size, use Image.contain() in a sized box, or allow flow content to split."
        )


def _content_box(node: LayoutNode, bounds: Rect) -> Rect:
    padding = node.style.padding
    return Rect(
        bounds.x + padding.left,
        bounds.y + padding.top,
        max(0.0, bounds.width - padding.horizontal),
        max(0.0, bounds.height - padding.vertical),
    )


def _outside(bounds: Rect, limit: Rect) -> bool:
    return (
        bounds.x < limit.x - 0.01 or bounds.y < limit.y - 0.01
        or bounds.right > limit.right + 0.01 or bounds.bottom > limit.bottom + 0.01
    )


def _in_page_flow(node: LayoutNode) -> bool:
    """Absolute regions and their descendants use physical-page diagnostics only."""
    current: LayoutNode | None = node
    while current is not None and current.node_type != "page":
        if current.style.position is PositionMode.ABSOLUTE:
            return False
        current = current.parent
    return current is not None


def paint_layout_diagnostics(
    adapter: ReportLabCanvasAdapter, page: LayoutNode, items: Sequence[RenderItem]
) -> None:
    """Show blue bounds, green content boxes and orange rectangular clip regions."""
    with adapter.isolated_state():
        page_bounds = Rect(0, 0, page.resolved_width, page.resolved_height)
        body_bounds = _content_box(page, page_bounds)
        adapter.draw_rect(body_bounds, stroke=CONTENT_COLOR, stroke_width=0.75)
        clips: set[Rect] = set()
        for item in items:
            bounds = item.absolute_bounds
            if _outside(bounds, page_bounds):
                warnings.warn(LayoutOverflowWarning(page.page_index + 1, item), stacklevel=3)
            elif _in_page_flow(item.node) and _outside(bounds, body_bounds):
                warnings.warn(LayoutOverflowWarning(page.page_index + 1, item, body_bounds), stacklevel=3)
            adapter.draw_rect(bounds, stroke=BOUNDS_COLOR, stroke_width=0.5)
            adapter.draw_rect(_content_box(item.node, bounds), stroke=CONTENT_COLOR, stroke_width=0.25)
            clips.update(item.clip_rects)
            if bounds.width > 24 and bounds.height >= 8:
                with adapter.isolated_state():
                    adapter.apply_clip_rect(bounds)
                    label = f"{item.node.name or item.node.node_type} [{page.page_index + 1}]"
                    # Debug labels use a base-14 font so diagnostics need no registered font.
                    label = label.encode("ascii", errors="backslashreplace").decode("ascii")
                    adapter.draw_text(
                        bounds.x + 1, bounds.y + 1, bounds.width - 2,
                        label[:80], "Helvetica", 5, 6, BOUNDS_COLOR, text_overflow="clip",
                    )
        for clip in clips:
            adapter.draw_rect(clip, stroke=CLIP_COLOR, stroke_width=0.75)
