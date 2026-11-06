"""Local alpha-mask shadows; foreground typography always remains native PDF text."""

from __future__ import annotations

import math
from collections.abc import Callable
from contextlib import closing
from ctypes import byref, c_float
from io import BytesIO
from threading import RLock
from typing import TYPE_CHECKING, Final, Protocol, cast

from PIL import Image, ImageChops, ImageFilter

from ..layout.node import Rect
from ..style.color import RGBA
from ..style.text_shadow import TextShadow

if TYPE_CHECKING:
    from pypdfium2 import PdfBitmap

    from .rl_adapter import ReportLabCanvasAdapter

# PDFium is process-global and must not be entered concurrently by our renderers.
_PDFIUM_LOCK: Final = RLock()
_MAX_MASK_PIXELS: Final = 16_000_000
_MASK_COLOR: Final = RGBA(1, 1, 1, 1)
ShadowPainter = Callable[["ReportLabCanvasAdapter", RGBA, float], None]


class _Rasterizer(Protocol):
    def __call__(
        self,
        *,
        scale: float,
        crop: tuple[float, float, float, float],
        fill_color: tuple[int, int, int, int],
        rev_byteorder: bool,
    ) -> PdfBitmap: ...


class GaussianShadowDependencyError(RuntimeError):
    """The explicit Gaussian mode requires the optional PDF rasterizer."""

    def __init__(self) -> None:
        super().__init__(
            'Gaussian text shadows require: pip install "smart-report[gaussian]"'
        )


class ShadowBoundsError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PDFium could not measure the shadow glyph bounds")


class ShadowRasterLimitError(ValueError):
    """A requested local shadow would allocate an excessive bitmap."""

    def __init__(self, pixels: int) -> None:
        self.pixels = pixels
        super().__init__(
            f"Shadow mask requires {pixels} pixels; limit is {_MAX_MASK_PIXELS}. Reduce dpi or text area."
        )


def paint_shadow(
    adapter: ReportLabCanvasAdapter, shadow: TextShadow, painter: ShadowPainter
) -> None:
    """Paint one isolated shadow pass, preserving parent clipping and foreground state."""
    if shadow.color.alpha == 0:
        return
    if shadow.method == "stroke":
        with adapter.isolated_state():
            painter(adapter, shadow.color, shadow.spread + shadow.blur * 0.5)
        return
    try:
        from pypdfium2 import PdfDocument
        from pypdfium2.raw import FPDFPageObj_GetBounds
    except ModuleNotFoundError as error:
        if error.name != "pypdfium2":
            raise
        raise GaussianShadowDependencyError() from error

    scale = shadow.dpi / 72
    extent = 4 * shadow.sigma + shadow.spread + 2
    if not math.isfinite(extent) or extent * scale > math.sqrt(_MAX_MASK_PIXELS):
        raise ShadowRasterLimitError(_MAX_MASK_PIXELS + 1)
    padding = math.ceil(extent)
    buffer = BytesIO()
    # Expand the temporary page so glyphs beyond an output-page edge can still cast a shadow.
    page_size = (adapter.page_width + 2 * padding, adapter.page_height + 2 * padding)
    mask_adapter = type(adapter)(buffer, page_size)
    mask_adapter.canvas.translate(padding, padding)
    painter(mask_adapter, _MASK_COLOR, 0)
    mask_adapter.save()

    with (
        _PDFIUM_LOCK,
        closing(PdfDocument(buffer.getvalue())) as pdf,
        closing(pdf[0]) as page,
    ):
        # The helper name changed in PDFium 5.x; its public C API remains stable.
        bounds: list[tuple[float, float, float, float]] = []
        for obj in page.get_objects():
            l, b, r, t = c_float(), c_float(), c_float(), c_float()
            if not FPDFPageObj_GetBounds(
                obj.raw, byref(l), byref(b), byref(r), byref(t)
            ):
                raise ShadowBoundsError()
            bounds.append((l.value, b.value, r.value, t.value))
        if not bounds:
            return
        left = max(0, math.floor((min(b[0] for b in bounds) - padding) * scale) / scale)
        bottom = max(
            0, math.floor((min(b[1] for b in bounds) - padding) * scale) / scale
        )
        right = min(
            page_size[0],
            math.ceil((max(b[2] for b in bounds) + padding) * scale) / scale,
        )
        top = min(
            page_size[1],
            math.ceil((max(b[3] for b in bounds) + padding) * scale) / scale,
        )
        pixels = math.ceil((right - left) * scale) * math.ceil((top - bottom) * scale)
        if pixels > _MAX_MASK_PIXELS:
            raise ShadowRasterLimitError(pixels)
        if right <= left or top <= bottom:
            return
        crop = (left, bottom, page_size[0] - right, page_size[1] - top)
        # PDFium documents float scale; its unannotated `scale=1` is inferred as int by Pyright.
        rasterize = cast(_Rasterizer, page.render)
        with closing(
            rasterize(
                scale=scale, crop=crop, fill_color=(0, 0, 0, 0), rev_byteorder=True
            )
        ) as bitmap:
            alpha = bitmap.to_pil().getchannel("A")
    # Figma's exported shadow filter uses a saturated SourceAlpha then `out`.
    hard_alpha = (
        alpha.point([min(255, i * 127) for i in range(256)])
        if shadow.knockout
        else alpha
    )
    if shadow.knockout:
        alpha = hard_alpha
    spread_pixels = round(shadow.spread * scale)
    if spread_pixels:
        alpha = alpha.filter(ImageFilter.MaxFilter(2 * spread_pixels + 1))
    if shadow.sigma:
        alpha = alpha.filter(ImageFilter.GaussianBlur(shadow.sigma * scale))
    if shadow.knockout:
        # The painter already offset the shadow glyph. Knock out original SourceAlpha,
        # not the displaced shadow itself; outside this local tile the mask is zero.
        original_alpha = hard_alpha.transform(
            hard_alpha.size,
            Image.Transform.AFFINE,
            (1, 0, shadow.x * scale, 0, 1, shadow.y * scale),
            resample=Image.Resampling.BILINEAR,
            fillcolor=0,
        )
        alpha = ImageChops.multiply(alpha, ImageChops.invert(original_alpha))
    alpha = alpha.point([round(i * shadow.color.alpha) for i in range(256)])
    rgb = tuple(
        round(c * 255)
        for c in (shadow.color.red, shadow.color.green, shadow.color.blue)
    )
    image = Image.new("RGBA", alpha.size, (*rgb, 0))
    image.putalpha(alpha)
    output = BytesIO()
    image.save(output, format="PNG")
    rect = Rect(
        left - padding,
        adapter.page_height - (top - padding),
        image.width / scale,
        image.height / scale,
    )
    with adapter.isolated_state():
        adapter.draw_image(output.getvalue(), rect)
