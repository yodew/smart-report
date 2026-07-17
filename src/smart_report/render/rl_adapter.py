"""ReportLab canvas adapter."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast

from ..layout.node import CornerRadii, Rect
from ..layout.rich_text_layout import RichTextLine
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
    def drawPath(self, path: object, stroke: int = 1, fill: int = 0) -> None: ...
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
    def setTitle(self, value: str) -> None: ...
    def setAuthor(self, value: str) -> None: ...
    def setSubject(self, value: str) -> None: ...
    def setKeywords(self, value: str) -> None: ...
    def bookmarkPage(self, key: str) -> None: ...
    def addOutlineEntry(self, title: str, key: str, level: int = 0, closed: bool = False) -> None: ...
    def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None: ...


class TextObjectLike(Protocol):
    def setFont(self, font_name: str, font_size: float, leading: float | None = None) -> None: ...
    def setFillColorRGB(self, r: float, g: float, b: float) -> None: ...
    def setTextOrigin(self, x: float, y: float) -> None: ...
    def setLeading(self, leading: float) -> None: ...
    def setCharSpace(self, charSpace: float) -> None: ...
    def textOut(self, text: str) -> None: ...
    def textLine(self, text: str = "") -> None: ...


class PathLike(Protocol):
    def rect(self, x: float, y: float, width: float, height: float) -> None: ...
    def roundRect(self, x: float, y: float, width: float, height: float, radius: float) -> None: ...
    def moveTo(self, x: float, y: float) -> None: ...
    def lineTo(self, x: float, y: float) -> None: ...
    def curveTo(self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None: ...
    def close(self) -> None: ...


class CanvasFactory(Protocol):
    def __call__(self, target: str | BytesIO, pagesize: tuple[float, float]) -> CanvasLike: ...


class SvgToDrawingFn(Protocol):
    def __call__(self, path: str) -> object: ...


class RenderDrawingFn(Protocol):
    def __call__(self, drawing: object, canvas: object, x: float, y: float) -> None: ...


class ReportLabCanvasAdapter:
    _canvas: CanvasLike
    page_width: float
    page_height: float

    def __init__(self, target: str | BytesIO, page_size: tuple[float, float]) -> None:
        canvas_module = import_module("reportlab.pdfgen.canvas")
        canvas_class = cast(CanvasFactory, getattr(canvas_module, "Canvas"))
        self._canvas = canvas_class(target, pagesize=page_size)
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

    def apply_clip_rounded_rect(self, rect: Rect, radius: CornerRadii) -> None:
        path = self._rounded_rect_path(rect, radius)
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
        radius: CornerRadii | None = None,
    ) -> None:
        self.set_fill(fill)
        self.set_stroke(stroke, stroke_width)
        rl_y = self.to_rl_y(rect.y, rect.height)
        stroke_flag = 1 if stroke is not None and stroke_width > 0 else 0
        fill_flag = 1 if fill is not None else 0
        radii = radius or CornerRadii()
        if not radii.is_zero:
            if radii.fitted(rect.width, rect.height).is_uniform:
                self._canvas.roundRect(rect.x, rl_y, rect.width, rect.height, radii.fitted(rect.width, rect.height).uniform_value, stroke=stroke_flag, fill=fill_flag)
                return
            self._canvas.drawPath(self._rounded_rect_path(rect, radii), stroke=stroke_flag, fill=fill_flag)
            return
        self._canvas.rect(rect.x, rl_y, rect.width, rect.height, stroke=stroke_flag, fill=fill_flag)

    def _rounded_rect_path(self, rect: Rect, radius: CornerRadii) -> PathLike:
        radii = radius.fitted(rect.width, rect.height)
        if radii.is_uniform:
            path = cast(PathLike, self._canvas.beginPath())
            path.roundRect(rect.x, self.to_rl_y(rect.y, rect.height), rect.width, rect.height, radii.uniform_value)
            return path

        kappa = 0.5522847498307936
        left = rect.x
        right = rect.right
        bottom = self.to_rl_y(rect.y, rect.height)
        top = bottom + rect.height
        tl = radii.top_left
        tr = radii.top_right
        br = radii.bottom_right
        bl = radii.bottom_left
        path = cast(PathLike, self._canvas.beginPath())
        path.moveTo(left + tl, top)
        path.lineTo(right - tr, top)
        if tr:
            path.curveTo(right - tr + (tr * kappa), top, right, top - tr + (tr * kappa), right, top - tr)
        else:
            path.lineTo(right, top)
        path.lineTo(right, bottom + br)
        if br:
            path.curveTo(right, bottom + br - (br * kappa), right - br + (br * kappa), bottom, right - br, bottom)
        else:
            path.lineTo(right, bottom)
        path.lineTo(left + bl, bottom)
        if bl:
            path.curveTo(left + bl - (bl * kappa), bottom, left, bottom + bl - (bl * kappa), left, bottom + bl)
        else:
            path.lineTo(left, bottom)
        path.lineTo(left, top - tl)
        if tl:
            path.curveTo(left, top - tl + (tl * kappa), left + tl - (tl * kappa), top, left + tl, top)
        else:
            path.lineTo(left, top)
        path.close()
        return path

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
        height: float | None = None,
        valign: str = "top",
        letter_spacing: float = 0.0,
        text_overflow: str = "wrap",
    ) -> None:
        if text_overflow in {"clip", "ellipsis"}:
            wrapped_lines = [text]
        else:
            wrapped_lines = wrap_text(text, width, font_name, font_size, typography=typography, text_direction=text_direction, letter_spacing=letter_spacing)
        text_height = max(line_height, len(wrapped_lines) * line_height)
        vertical_offset = 0.0
        if height is not None:
            extra_height = max(0.0, height - text_height)
            if valign == "middle":
                vertical_offset = extra_height / 2.0
            elif valign == "bottom":
                vertical_offset = extra_height
        baseline_y = self.page_height - y - vertical_offset - font_size
        text_object = cast(TextObjectLike, self._canvas.beginText(x, baseline_y))
        text_object.setFont(font_name, font_size, line_height)
        text_object.setLeading(line_height)
        text_object.setCharSpace(letter_spacing)
        text_color = color or DEFAULT_TEXT_COLOR
        text_object.setFillColorRGB(text_color.red, text_color.green, text_color.blue)
        self._canvas.setFillAlpha(text_color.alpha)
        current_baseline_y = baseline_y
        for line in wrapped_lines:
            display_line = shape_text(line, typography, text_direction)
            line_width = (shaped_string_width(display_line, font_name, font_size) if typography == "advanced" else string_width(display_line, font_name, font_size)) + max(0, len(display_line) - 1) * letter_spacing
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

    def draw_rich_text(
        self,
        x: float,
        y: float,
        width: float,
        lines: list[RichTextLine],
        align: str = "left",
        height: float | None = None,
        valign: str = "top",
    ) -> None:
        text_height = sum(line.height for line in lines)
        vertical_offset = 0.0
        if height is not None:
            extra_height = max(0.0, height - text_height)
            if valign == "middle":
                vertical_offset = extra_height / 2.0
            elif valign == "bottom":
                vertical_offset = extra_height
        baseline_y = self.page_height - y - vertical_offset
        text_object = cast(TextObjectLike, self._canvas.beginText(x, baseline_y))
        current_baseline_y = baseline_y
        for line in lines:
            max_font_size = max((fragment.font_size for fragment in line.fragments), default=12.0)
            current_baseline_y -= max_font_size
            offset = max(0.0, width - line.width)
            if align == "center":
                offset /= 2.0
            elif align == "left":
                offset = 0.0
            text_object.setTextOrigin(x + offset, current_baseline_y)
            for fragment in line.fragments:
                text_object.setFont(fragment.font_name, fragment.font_size, line.height)
                text_object.setCharSpace(fragment.letter_spacing)
                text_color = fragment.color or DEFAULT_TEXT_COLOR
                text_object.setFillColorRGB(text_color.red, text_color.green, text_color.blue)
                self._canvas.setFillAlpha(text_color.alpha)
                text_object.textOut(fragment.text)
            text_object.textLine()
            current_baseline_y -= max(0.0, line.height - max_font_size)
        self._canvas.drawText(text_object)

    def draw_image(self, image_source: str | bytes, rect: Rect, opacity: float = 1.0, fit: str = "stretch", radius: CornerRadii | None = None) -> None:
        if isinstance(image_source, str) and Path(image_source).suffix.lower() == ".svg":
            self.draw_svg(image_source, rect, opacity=opacity, fit=fit, radius=radius)
            return

        if opacity < 1.0:
            self._canvas.setFillAlpha(opacity)
            self._canvas.setStrokeAlpha(opacity)
        image_reader = self._image_reader(image_source)
        draw_rect = self._fit_rect(rect, self._image_size(image_reader), fit)
        if fit == "cover":
            self.apply_clip_rect(rect)
        if radius is not None and not radius.is_zero:
            self.apply_clip_rounded_rect(draw_rect, radius)
        self._canvas.drawImage(image_reader, draw_rect.x, self.to_rl_y(draw_rect.y, draw_rect.height), draw_rect.width, draw_rect.height, mask="auto")

    def draw_svg(self, image_path: str, rect: Rect, opacity: float = 1.0, fit: str = "stretch", radius: CornerRadii | None = None) -> None:
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
        if radius is not None and not radius.is_zero:
            self.apply_clip_rounded_rect(draw_rect, radius)
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

    def set_metadata(
        self,
        title: str | None = None,
        author: str | None = None,
        subject: str | None = None,
        keywords: str | None = None,
    ) -> None:
        setters = {
            "setTitle": title,
            "setAuthor": author,
            "setSubject": subject,
            "setKeywords": keywords,
        }
        for method_name, value in setters.items():
            if value is not None:
                setter = getattr(self._canvas, method_name, None)
                if setter is not None:
                    setter(value)

    def bookmark_page(self, key: str) -> None:
        method = getattr(self._canvas, "bookmarkPage", None)
        if method is not None:
            method(key)

    def add_outline_entry(self, title: str, key: str, level: int = 0) -> None:
        method = getattr(self._canvas, "addOutlineEntry", None)
        if method is not None:
            method(title, key, level=level, closed=False)

    def link_url(self, url: str, rect: Rect) -> None:
        bottom = self.to_rl_y(rect.y, rect.height)
        self._canvas.linkURL(url, (rect.x, bottom, rect.x + rect.width, bottom + rect.height), relative=0)

    def save(self) -> None:
        self._canvas.save()
