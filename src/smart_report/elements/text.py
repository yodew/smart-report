"""Text element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


class Text(NodeBuilder):
    def __init__(self, text: str) -> None:
        node = LayoutNode(node_type="text", style=Style(), content={"text": text})
        super().__init__(node)

    def text(self, value: str) -> "Text":
        self.node.content["text"] = value
        return self
