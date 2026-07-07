"""Image element builder."""

from __future__ import annotations

import base64
from os import PathLike, fspath
from io import BytesIO
from pathlib import Path

from .._builder_core import NodeBuilder
from ..layout.node import LayoutNode, Style

ImageSource = str | bytes | PathLike[str]


class Image(NodeBuilder):
    def __init__(self, src: ImageSource) -> None:
        node = LayoutNode(node_type="image", style=Style(), content={})
        super().__init__(node)
        self.src(src)

    def src(self, value: ImageSource) -> "Image":
        if isinstance(value, bytes):
            self.node.content["src_bytes"] = value
            self.node.content.pop("src", None)
            _set_intrinsic_size(self.node, value)
            return self

        source = fspath(value)
        if source.startswith("data:image/"):
            _prefix, _separator, payload = source.partition(",")
            self.node.content["src_bytes"] = base64.b64decode(payload)
            self.node.content.pop("src", None)
            _set_intrinsic_size(self.node, self.node.content["src_bytes"])
            return self
        self.node.content["src"] = source
        self.node.content.pop("src_bytes", None)
        _set_intrinsic_size(self.node, source)
        return self

    def fit(self, value: str) -> "Image":
        normalized = value.lower()
        if normalized not in {"stretch", "contain", "cover"}:
            raise ValueError(f"Unsupported image fit: {value}")
        self.node.content["object_fit"] = normalized
        return self

    def contain(self) -> "Image":
        return self.fit("contain")

    def cover(self) -> "Image":
        return self.fit("cover")

    def bytes(self, value: bytes) -> "Image":
        self.node.content["src_bytes"] = value
        self.node.content.pop("src", None)
        _set_intrinsic_size(self.node, value)
        return self


def _set_intrinsic_size(node: LayoutNode, source: str | bytes | object) -> None:
    try:
        from PIL import Image as PillowImage

        if isinstance(source, bytes):
            image_source = BytesIO(source)
        elif isinstance(source, str):
            if Path(source).suffix.lower() == ".svg":
                return
            image_source = source
        else:
            return
        with PillowImage.open(image_source) as image:
            width, height = image.size
            node.content["intrinsic_width"] = float(width)
            node.content["intrinsic_height"] = float(height)
    except Exception:
        node.content.pop("intrinsic_width", None)
        node.content.pop("intrinsic_height", None)
