"""Text element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


LetterSpacingInput = str | int | float


class Text(NodeBuilder):
    """Chainable text element builder.

    Text supports fixed text boxes via ``width(...)`` / ``height(...)`` or
    ``size(...)``. Use ``align(...)`` for horizontal alignment and
    ``valign(...)`` for vertical alignment inside that text box.
    """

    def __init__(self, text: str) -> None:
        """Create a text node with the given string content."""

        node = LayoutNode(node_type="text", style=Style(), content={"text": text})
        super().__init__(node)

    def text(self, value: str) -> "Text":
        """Replace the text content and return this builder."""

        self.node.content["text"] = value
        return self

    def align(self, value: str) -> "Text":
        """Set horizontal text alignment inside the text box.

        Accepted values are ``"left"``, ``"center"``, and ``"right"``.
        For centering to be visible, give the text node a width, for example
        ``add_text("Title").width("100%").align("center")``.
        """

        normalized = value.lower()
        if normalized not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported text alignment: {value}")
        self.node.content["align"] = normalized
        return self

    def valign(self, value: str) -> "Text":
        """Set vertical text alignment inside the text box.

        Accepted values are ``"top"``, ``"middle"``, and ``"bottom"``.
        For vertical centering to be visible, give the text node a height, for
        example ``add_text("...").size("100%", "100%").valign("middle")``.
        """

        normalized = value.lower()
        if normalized not in {"top", "middle", "bottom"}:
            raise ValueError(f"Unsupported text vertical alignment: {value}")
        self.node.content["valign"] = normalized
        return self

    def letter_spacing(self, value: LetterSpacingInput) -> "Text":
        """Set extra spacing between characters.

        Accepted formats:
        - number: points, e.g. ``0.5`` means 0.5 pt
        - ``"0.05em"``: fraction of current font size
        - ``"5%"``: percentage of current font size

        ``"0.05em"`` and ``"5%"`` are equivalent: both become 5% of the
        current font size.
        """

        self.node.content["letter_spacing"] = _normalize_letter_spacing(value)
        return self

    def link(self, url: object) -> "Text":
        """Add an external URL link annotation to the whole text node.

        ``url`` must be a non-empty string. The link rectangle follows text
        wrapping, horizontal alignment, and vertical alignment.
        """

        if not isinstance(url, str):
            raise TypeError("Text.link url must be a string")
        if not url.strip():
            raise ValueError("Text.link url must not be empty")
        self.node.content["link_url"] = url
        return self


def _normalize_letter_spacing(value: LetterSpacingInput) -> str | float:
    if isinstance(value, (int, float)):
        return float(value)
    normalized = value.strip().lower()
    if normalized.endswith("em"):
        float(normalized[:-2])
        return normalized
    if normalized.endswith("%"):
        float(normalized[:-1])
        return normalized
    return float(normalized)
