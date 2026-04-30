"""Pass 2: resolve widths top-down."""

from __future__ import annotations

from .node import LayoutNode
from ..style.units import Percent
from ..style.units import resolve_size


def resolve_widths(root: LayoutNode, available_width: float | None = None) -> None:
    """Resolve all node widths using a top-down traversal.

    The parent content box is the reference for child percentage widths.
    """

    root_width = available_width if available_width is not None else root.resolved_width
    _resolve_node_width(root, root_width)


def _resolve_node_width(node: LayoutNode, available_width: float) -> None:
    width_reference = available_width
    auto_width = available_width
    if node.style.position.value == "flow":
        flow_width = max(0.0, available_width - node.style.margin.horizontal)
        auto_width = flow_width
        if isinstance(node.style.width, Percent):
            width_reference = flow_width

    node.resolved_width = max(0.0, resolve_size(node.style.width, width_reference, auto_width))

    child_reference_width = max(0.0, node.resolved_width - node.style.padding.horizontal)
    for child in node.children:
        _resolve_node_width(child, child_reference_width)
