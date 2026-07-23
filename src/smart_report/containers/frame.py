"""Frame container builder."""

from __future__ import annotations

from os import PathLike

from .._builder_core import ContainerBuilder
from ..layout.node import LayoutNode, Style
from ..style.units import parse_size


class Frame(ContainerBuilder):
    """Flow container for report content."""

    def __init__(self) -> None:
        """Create an auto-height full-width frame."""

        style = Style(width=parse_size("100%"), height=parse_size("auto"))
        super().__init__(LayoutNode(node_type="frame", style=style))

    def background_image(self, src: str | bytes | PathLike[str], *, fit: str = "cover", opacity: float = 1.0) -> "Frame":
        """Set a background image for this frame."""

        return super().background_image(src, fit=fit, opacity=opacity)
