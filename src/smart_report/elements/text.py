"""Text element builder."""

from __future__ import annotations

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style


LetterSpacingInput = str | int | float


class Text(NodeBuilder):
    def __init__(self, text: str) -> None:
        node = LayoutNode(node_type="text", style=Style(), content={"text": text})
        super().__init__(node)

    def text(self, value: str) -> "Text":
        self.node.content["text"] = value
        return self

    def align(self, value: str) -> "Text":
        normalized = value.lower()
        if normalized not in {"left", "center", "right"}:
            raise ValueError(f"Unsupported text alignment: {value}")
        self.node.content["align"] = normalized
        return self

    def valign(self, value: str) -> "Text":
        normalized = value.lower()
        if normalized not in {"top", "middle", "bottom"}:
            raise ValueError(f"Unsupported text vertical alignment: {value}")
        self.node.content["valign"] = normalized
        return self

    def letter_spacing(self, value: LetterSpacingInput) -> "Text":
        self.node.content["letter_spacing"] = _normalize_letter_spacing(value)
        return self

    def link(self, url: object) -> "Text":
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
