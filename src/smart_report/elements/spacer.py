"""Spacer element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style
from ..style.units import Fixed, SizeInput, parse_size


class Spacer(NodeBuilder):
    def __init__(self, height: SizeInput) -> None:
        parsed = parse_size(height)
        fixed_height = parsed.points if isinstance(parsed, Fixed) else 0.0
        node = LayoutNode(node_type="spacer", style=Style(height=Fixed(fixed_height)), content={"height": fixed_height})
        super().__init__(node)
