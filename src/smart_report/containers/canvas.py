"""Canvas container builder."""

from __future__ import annotations

from .._builder_core import ContainerBuilder
from ..layout.node import LayoutNode, Style
from ..style.units import parse_size


class Canvas(ContainerBuilder):
    def __init__(self) -> None:
        style = Style(width=parse_size("100%"), height=parse_size("auto"))
        super().__init__(LayoutNode(node_type="canvas", style=style))
