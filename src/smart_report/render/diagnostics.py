"""Opt-in PDF layout overlays, drawn after normal content without changing layout."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Final

from ..layout.node import LayoutNode, Rect, RenderItem
from ..style.color import RGBA
from .rl_adapter import ReportLabCanvasAdapter

BOUNDS_COLOR: Final = RGBA(0.1, 0.35, 0.9, 0.85)
CONTENT_COLOR: Final = RGBA(0.0, 0.6, 0.3, 0.85)
CLIP_COLOR: Final = RGBA(1.0, 0.45, 0.0, 0.9)


class LayoutOverflowWarning(UserWarning):
    """A named node extends beyond the physical PDF page in debug mode."""

    def __init__(self, page_number: int, item: RenderItem) -> None:
        self.page_number = page_number
        self.node_name = item.node.name or item.node.node_type
        self.bounds = item.absolute_bounds
        super().__init__(
            f"Page {page_number}: {self.node_name!r} ({item.node.node_type}) "
            f"bounds={self.bounds} exceed the physical page. "
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


def paint_layout_diagnostics(
    adapter: ReportLabCanvasAdapter, page: LayoutNode, items: Sequence[RenderItem]
) -> None:
    """Show blue bounds, green content boxes and orange rectangular clip regions."""
    with adapter.isolated_state():
        adapter.draw_rect(
            _content_box(page, Rect(0, 0, page.resolved_width, page.resolved_height)),
            stroke=CONTENT_COLOR, stroke_width=0.75,
        )
        clips: set[Rect] = set()
        for item in items:
            bounds = item.absolute_bounds
            if (
                bounds.x < -0.01 or bounds.y < -0.01
                or bounds.right > page.resolved_width + 0.01
                or bounds.bottom > page.resolved_height + 0.01
            ):
                warnings.warn(LayoutOverflowWarning(page.page_index + 1, item), stacklevel=3)
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
