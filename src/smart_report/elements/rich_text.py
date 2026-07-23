"""Rich text element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style
from ..style.color import RGBA
from ..style.letter_spacing import LetterSpacingInput, normalize_letter_spacing


class RichText(NodeBuilder):
    """Chainable rich text element builder for styled inline spans."""

    def __init__(self, text: str = "") -> None:
        """Create a rich text node, optionally initialized with plain text."""

        node = LayoutNode(node_type="rich_text", style=Style(), content={"runs": []})
        super().__init__(node)
        if text:
            self.text(text)

    def text(self, value: str) -> "RichText":
        """Replace all runs with one plain text run and return this builder."""

        self.node.content["runs"] = [{"kind": "text", "text": value}]
        return self

    def span(
        self,
        text: str,
        *,
        font: str | None = None,
        font_family: str | None = None,
        font_size: float | None = None,
        color: str | RGBA | None = None,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        letter_spacing: LetterSpacingInput | None = None,
    ) -> "RichText":
        """Append a styled inline text span and return this builder."""

        run: dict[str, object] = {"kind": "text", "text": text}
        if font is not None:
            run["font"] = font
        if font_family is not None:
            run["font_family"] = font_family
        if font_size is not None:
            run["font_size"] = float(font_size)
        if color is not None:
            run["color"] = _serializable_color(color)
        if bold:
            run["bold"] = True
        if italic:
            run["italic"] = True
        if underline:
            run["underline"] = True
        if letter_spacing is not None:
            run["letter_spacing"] = normalize_letter_spacing(letter_spacing)
        _runs(self.node).append(run)
        return self

    def letter_spacing(self, value: LetterSpacingInput) -> "RichText":
        """Set default extra spacing between characters for all spans.

        A span-level ``letter_spacing`` argument overrides this value for
        that span. Numbers are points; ``"0.05em"`` and ``"5%"`` resolve
        against each span's effective font size.
        """

        self.node.content["letter_spacing"] = normalize_letter_spacing(value)
        return self

    def br(self, count: int = 1) -> "RichText":
        """Append one or more hard line breaks and return this builder."""

        if count < 1:
            raise ValueError("RichText.br count must be >= 1")
        runs = _runs(self.node)
        for _ in range(count):
            runs.append({"kind": "br"})
        return self

    def clear(self) -> "RichText":
        """Remove all rich text runs and return this builder."""

        self.node.content["runs"] = []
        return self

    def align(self, value: str) -> "RichText":
        """Set horizontal rich text alignment inside the text box."""

        normalized = value.lower()
        if normalized not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported rich text alignment: {value}")
        self.node.content["align"] = normalized
        return self

    def valign(self, value: str) -> "RichText":
        """Set vertical rich text alignment inside the text box."""

        normalized = value.lower()
        if normalized not in {"top", "middle", "bottom"}:
            raise ValueError(f"Unsupported rich text vertical alignment: {value}")
        self.node.content["valign"] = normalized
        return self


def _runs(node: LayoutNode) -> list[dict[str, object]]:
    runs = node.content.get("runs")
    if not isinstance(runs, list):
        runs = []
        node.content["runs"] = runs
    return runs


def _serializable_color(color: str | RGBA) -> str | list[float]:
    if isinstance(color, str):
        return color
    return [color.red, color.green, color.blue, color.alpha]
