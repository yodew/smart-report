"""Image element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


class Image(NodeBuilder):
    def __init__(self, src: str) -> None:
        node = LayoutNode(node_type="image", style=Style(), content={"src": src})
        super().__init__(node)

    def src(self, value: str) -> "Image":
        self.node.content["src"] = value
        return self
