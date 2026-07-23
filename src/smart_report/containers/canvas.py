"""Canvas container builder."""

from __future__ import annotations

from os import PathLike

from .._builder_core import ContainerBuilder
from ..layout.node import LayoutNode, Style
from ..style.units import parse_size


class Canvas(ContainerBuilder):
    """Layered container for absolute positioning and overlays."""

    def __init__(self) -> None:
        """Create an auto-height full-width canvas."""

        style = Style(width=parse_size("100%"), height=parse_size("auto"))
        super().__init__(LayoutNode(node_type="canvas", style=style))

    def background_image(self, src: str | bytes | PathLike[str], *, fit: str = "cover", opacity: float = 1.0) -> "Canvas":
        """Set a background image for this canvas."""

        return super().background_image(src, fit=fit, opacity=opacity)
