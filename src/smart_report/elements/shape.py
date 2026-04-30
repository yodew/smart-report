"""Shape element builders."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


class Rect(NodeBuilder):
    def __init__(self) -> None:
        super().__init__(LayoutNode(node_type="rect", style=Style()))


class Line(NodeBuilder):
    def __init__(self) -> None:
        super().__init__(LayoutNode(node_type="line", style=Style()))
