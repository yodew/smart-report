"""Spacer element builder."""

from __future__ import annotations

from math import isfinite

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style
from ..style.units import Fixed, SizeInput, parse_size


class Spacer(NodeBuilder):
    """Fixed-height empty flow element."""

    def __init__(self, height: SizeInput) -> None:
        """Create a spacer with a fixed non-negative height."""

        parsed = parse_size(height)
        if not isinstance(parsed, Fixed):
            raise ValueError("Spacer height requires a fixed point-compatible value")
        fixed_height = parsed.points
        if not isfinite(fixed_height) or fixed_height < 0:
            raise ValueError("Spacer height must be a finite non-negative value")
        node = LayoutNode(node_type="spacer", style=Style(height=Fixed(fixed_height)), content={"height": fixed_height})
        super().__init__(node)
