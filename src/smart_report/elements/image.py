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
    """Chainable image element builder.

    Sources may be string paths, ``pathlib.Path`` values, bytes, or
    ``data:image/...;base64,...`` strings.
    """

    def __init__(self, src: ImageSource) -> None:
        """Create an image node from a local path, Path, bytes, or data URL."""

        node = LayoutNode(node_type="image", style=Style(), content={})
        super().__init__(node)
        self.src(src)

    def src(self, value: ImageSource) -> "Image":
        """Replace the image source.

        Local paths are stored as strings internally. PNG/JPEG intrinsic size
        is measured when possible; SVG size is resolved during rendering.
        """

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
        """Set how the image fits its box.

        Accepted values are ``"stretch"``, ``"contain"``, and ``"cover"``.
        ``stretch`` fills the box, ``contain`` preserves the full image, and
        ``cover`` preserves aspect ratio while cropping overflow.
        """

        normalized = value.lower()
        if normalized not in {"stretch", "contain", "cover"}:
            raise ValueError(f"Unsupported image fit: {value}")
        self.node.content["object_fit"] = normalized
        return self

    def contain(self) -> "Image":
        """Preserve aspect ratio and fit the whole image inside the box."""

        return self.fit("contain")

    def cover(self) -> "Image":
        """Preserve aspect ratio and fill the box, cropping overflow."""

        return self.fit("cover")

    def bytes(self, value: bytes) -> "Image":
        """Replace the image source with raw image bytes."""

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
