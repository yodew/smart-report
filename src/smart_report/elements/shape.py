"""Shape element builders."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style
from ..layout.text_overflow import normalize_text_overflow
from ..style.letter_spacing import LetterSpacingInput, normalize_letter_spacing


class Rect(NodeBuilder):
    """Rectangle shape builder."""

    def __init__(self, text: str | None = None) -> None:
        """Create a rectangle node, optionally with centered label text."""

        super().__init__(LayoutNode(node_type="rect", style=Style()))
        if text is not None:
            self.text(text)

    def text(self, value: str | None) -> "Rect":
        """Set or clear plain text rendered inside the rectangle."""

        if value is None:
            _ = self.node.content.pop("text", None)
            return self
        self.node.content["text"] = str(value)
        self.node.content.setdefault("align", "center")
        self.node.content.setdefault("valign", "middle")
        self.node.content.setdefault("text_overflow", "ellipsis")
        return self

    def align(self, value: str) -> "Rect":
        """Set horizontal alignment for rectangle text."""

        normalized = value.lower()
        if normalized not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported text alignment: {value}")
        self.node.content["align"] = normalized
        return self

    def valign(self, value: str) -> "Rect":
        """Set vertical alignment for rectangle text."""

        normalized = value.lower()
        if normalized not in {"top", "middle", "bottom"}:
            raise ValueError(f"Unsupported text vertical alignment: {value}")
        self.node.content["valign"] = normalized
        return self

    def letter_spacing(self, value: LetterSpacingInput) -> "Rect":
        """Set letter spacing for rectangle text."""

        self.node.content["letter_spacing"] = normalize_letter_spacing(value)
        return self

    def text_overflow(self, value: str) -> "Rect":
        """Set overflow handling for rectangle text."""

        self.node.content["text_overflow"] = normalize_text_overflow(value)
        return self


class Line(NodeBuilder):
    """Line shape builder."""

    def __init__(self) -> None:
        """Create a line node."""

        super().__init__(LayoutNode(node_type="line", style=Style()))
