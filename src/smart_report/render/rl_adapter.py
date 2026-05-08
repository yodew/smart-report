"""ReportLab canvas adapter."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from ..layout.node import Rect
from ..layout.text_wrap import wrap_text
from ..style.color import RGBA
from ..style.font import resolve_text_runs, shaped_string_width, string_width
from ..style.typography import TextDirection, TypographyMode, shape_text

DEFAULT_TEXT_COLOR = RGBA(0.0, 0.0, 0.0, 1.0)


class CanvasLike(Protocol):
    def saveState(self) -> None: ...
    def restoreState(self) -> None: ...
    def setFillColorRGB(self, r: float, g: float, b: float) -> None: ...
    def setStrokeColorRGB(self, r: float, g: float, b: float) -> None: ...
    def setFillAlpha(self, alpha: float) -> None: ...
    def setStrokeAlpha(self, alpha: float) -> None: ...
    def setLineWidth(self, width: float) -> None: ...
    def rect(self, x: float, y: float, width: float, height: float, stroke: int = 1, fill: int = 0) -> None: ...
    def roundRect(self, x: float, y: float, width: float, height: float, radius: float, stroke: int = 1, fill: int = 0) -> None: ...
    def line(self, x1: float, y1: float, x2: float, y2: float) -> None: ...
    def beginPath(self) -> object: ...
    def clipPath(self, path: object, stroke: int = 0, fill: int = 0) -> None: ...
    def setFont(self, font_name: str, font_size: float, leading: float | None = None) -> None: ...
    def beginText(self, x: float, y: float) -> object: ...
    def drawText(self, text_object: object) -> None: ...
    def drawImage(self, image: object, x: float, y: float, width: float, height: float, mask: object | None = None) -> None: ...
    def translate(self, dx: float, dy: float) -> None: ...
    def scale(self, x: float, y: float) -> None: ...
    def setPageSize(self, size: tuple[float, float]) -> None: ...
    def showPage(self) -> None: ...
    def save(self) -> None: ...


class TextObjectLike(Protocol):
    def setFont(self, font_name: str, font_size: float, leading: float | None = None) -> None: ...
    def setFillColorRGB(self, r: float, g: float, b: float) -> None: ...
    def setTextOrigin(self, x: float, y: float) -> None: ...
    def setLeading(self, leading: float) -> None: ...
    def textOut(self, text: str) -> None: ...
    def textLine(self, text: str = "") -> None: ...


class PathLike(Protocol):
    def rect(self, x: float, y: float, width: float, height: float) -> None: ...
    def roundRect(self, x: float, y: float, width: float, height: float, radius: float) -> None: ...


class CanvasFactory(Protocol):
    def __call__(self, file_path: str, pagesize: tuple[float, float]) -> CanvasLike: ...


class SvgToDrawingFn(Protocol):
    def __call__(self, path: str) -> object: ...


class RenderDrawingFn(Protocol):
    def __call__(self, drawing: object, canvas: object, x: float, y: float) -> None: ...


class ReportLabCanvasAdapter:
    _canvas: CanvasLike
    page_width: float
    page_height: float

    def __init__(self, file_path: str, page_size: tuple[float, float]) -> None:
        canvas_module = import_module("reportlab.pdfgen.canvas")
        canvas_class = cast(CanvasFactory, getattr(canvas_module, "Canvas"))
        self._canvas = canvas_class(file_path, pagesize=page_size)
        self.page_width, self.page_height = page_size

    @property
    def canvas(self) -> CanvasLike:
        return self._canvas

    @contextmanager
    def isolated_state(self) -> Iterator[CanvasLike]:
        self._canvas.saveState()
        try:
            yield self._canvas
        finally:
            self._canvas.restoreState()

    def set_page_size(self, page_size: tuple[float, float]) -> None:
        self.page_width, self.page_height = page_size
        self._canvas.setPageSize(page_size)

    def to_rl_y(self, top_y: float, height: float) -> float:
        return self.page_height - top_y - height

    def apply_clip_rect(self, rect: Rect) -> None:
        path = cast(PathLike, self._canvas.beginPath())
        path.rect(rect.x, self.to_rl_y(rect.y, rect.height), rect.width, rect.height)
        self._canvas.clipPath(path, stroke=0, fill=0)

    def apply_clip_rounded_rect(self, rect: Rect, radius: float) -> None:
        path = cast(PathLike, self._canvas.beginPath())
        path.roundRect(rect.x, self.to_rl_y(rect.y, rect.height), rect.width, rect.height, radius)
        self._canvas.clipPath(path, stroke=0, fill=0)

    def set_fill(self, color: RGBA | None) -> None:
        if color is None:
            return
        self._canvas.setFillColorRGB(color.red, color.green, color.blue)
        self._canvas.setFillAlpha(color.alpha)

    def set_stroke(self, color: RGBA | None, stroke_width: float) -> None:
        if color is None or stroke_width <= 0:
            return
        self._canvas.setStrokeColorRGB(color.red, color.green, color.blue)
        self._canvas.setStrokeAlpha(color.alpha)
        self._canvas.setLineWidth(stroke_width)

    def draw_rect(
        self,
        rect: Rect,
        fill: RGBA | None = None,
        stroke: RGBA | None = None,
        stroke_width: float = 0.0,
        radius: float = 0.0,
    ) -> None:
        self.set_fill(fill)
        self.set_stroke(stroke, stroke_width)
        rl_y = self.to_rl_y(rect.y, rect.height)
        stroke_flag = 1 if stroke is not None and stroke_width > 0 else 0
        fill_flag = 1 if fill is not None else 0
        if radius > 0:
            self._canvas.roundRect(rect.x, rl_y, rect.width, rect.height, radius, stroke=stroke_flag, fill=fill_flag)
            return
        self._canvas.rect(rect.x, rl_y, rect.width, rect.height, stroke=stroke_flag, fill=fill_flag)

    def draw_text(
        self,
        x: float,
        y: float,
        width: float,
        text: str,
        font_name: str,
        font_size: float,
        line_height: float,
        color: RGBA | None,
        typography: TypographyMode = "plain",
        text_direction: TextDirection = "auto",
        align: str = "left",
    ) -> None:
        wrapped_lines = wrap_text(text, width, font_name, font_size, typography=typography, text_direction=text_direction)
        baseline_y = self.page_height - y - font_size
        text_object = cast(TextObjectLike, self._canvas.beginText(x, baseline_y))
        text_object.setFont(font_name, font_size, line_height)
        text_object.setLeading(line_height)
        text_color = color or DEFAULT_TEXT_COLOR
        text_object.setFillColorRGB(text_color.red, text_color.green, text_color.blue)
        self._canvas.setFillAlpha(text_color.alpha)
        current_baseline_y = baseline_y
        for line in wrapped_lines:
            display_line = shape_text(line, typography, text_direction)
            line_width = shaped_string_width(display_line, font_name, font_size) if typography == "advanced" else string_width(display_line, font_name, font_size)
            offset = max(0.0, width - line_width)
            if align == "center":
                offset /= 2
            elif align == "left" and text_direction != "rtl":
                offset = 0.0
            text_object.setTextOrigin(x + offset, current_baseline_y)
            for run in resolve_text_runs(display_line, font_name):
                text_object.setFont(run.font_name, font_size, line_height)
                text_object.textOut(run.text)
            text_object.textLine()
            current_baseline_y -= line_height
        self._canvas.drawText(text_object)

    def draw_image(self, image_source: str | bytes, rect: Rect, opacity: float = 1.0, fit: str = "stretch") -> None:
        if isinstance(image_source, str) and Path(image_source).suffix.lower() == ".svg":
            self.draw_svg(image_source, rect, opacity=opacity, fit=fit)
            return

        if opacity < 1.0:
            self._canvas.setFillAlpha(opacity)
            self._canvas.setStrokeAlpha(opacity)
        image_reader = self._image_reader(image_source)
        draw_rect = self._fit_rect(rect, self._image_size(image_reader), fit)
        if fit == "cover":
            self.apply_clip_rect(rect)
        self._canvas.drawImage(image_reader, draw_rect.x, self.to_rl_y(draw_rect.y, draw_rect.height), draw_rect.width, draw_rect.height, mask="auto")

    def draw_svg(self, image_path: str, rect: Rect, opacity: float = 1.0, fit: str = "stretch") -> None:
        svglib_module = import_module("svglib.svglib")
        render_pdf_module = import_module("reportlab.graphics.renderPDF")
        svg_to_drawing = cast(SvgToDrawingFn, getattr(svglib_module, "svg2rlg"))
        render_draw = cast(RenderDrawingFn, getattr(render_pdf_module, "draw"))

        drawing = svg_to_drawing(image_path)
        if drawing is None:
            raise ValueError(f"Unable to parse SVG image: {image_path}")

        drawing_width = float(getattr(drawing, "width", rect.width) or rect.width)
        drawing_height = float(getattr(drawing, "height", rect.height) or rect.height)
        draw_rect = self._fit_rect(rect, (drawing_width, drawing_height), fit)
        scale_x = draw_rect.width / drawing_width if drawing_width else 1.0
        scale_y = draw_rect.height / drawing_height if drawing_height else 1.0

        if opacity < 1.0:
            self._canvas.setFillAlpha(opacity)
            self._canvas.setStrokeAlpha(opacity)

        if fit == "cover":
            self.apply_clip_rect(rect)
        self._canvas.translate(draw_rect.x, self.to_rl_y(draw_rect.y, draw_rect.height))
        self._canvas.scale(scale_x, scale_y)
        render_draw(drawing, self._canvas, 0.0, 0.0)

    def _image_reader(self, image_source: str | bytes) -> object:
        image_module = import_module("reportlab.lib.utils")
        image_reader = getattr(image_module, "ImageReader")
        if isinstance(image_source, bytes):
            return image_reader(BytesIO(image_source))
        return image_reader(image_source)

    def _image_size(self, image_reader: object) -> tuple[float, float]:
        get_size = getattr(image_reader, "getSize")
        width, height = cast(tuple[int, int], get_size())
        return float(width), float(height)

    def _fit_rect(self, rect: Rect, intrinsic_size: tuple[float, float], fit: str) -> Rect:
        intrinsic_width, intrinsic_height = intrinsic_size
        if fit not in {"contain", "cover"} or intrinsic_width <= 0 or intrinsic_height <= 0:
            return rect
        scale_x = rect.width / intrinsic_width
        scale_y = rect.height / intrinsic_height
        scale = min(scale_x, scale_y) if fit == "contain" else max(scale_x, scale_y)
        width = intrinsic_width * scale
        height = intrinsic_height * scale
        return Rect(
            x=rect.x + ((rect.width - width) / 2.0),
            y=rect.y + ((rect.height - height) / 2.0),
            width=width,
            height=height,
        )

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: RGBA | None, stroke_width: float) -> None:
        self.set_stroke(color, stroke_width)
        self._canvas.line(x1, self.page_height - y1, x2, self.page_height - y2)

    def show_page(self) -> None:
        self._canvas.showPage()

    def save(self) -> None:
        self._canvas.save()
