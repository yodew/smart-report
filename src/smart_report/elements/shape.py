"""Shape element builders."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


class Rect(NodeBuilder):
    """Rectangle shape builder."""

    def __init__(self) -> None:
        """Create a rectangle node."""

        super().__init__(LayoutNode(node_type="rect", style=Style()))


class Line(NodeBuilder):
    """Line shape builder."""

    def __init__(self) -> None:
        """Create a line node."""

        super().__init__(LayoutNode(node_type="line", style=Style()))
