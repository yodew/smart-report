"""Font registration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast


DEFAULT_FONT_NAME = "Helvetica"
TTFontFactory = Callable[[str, str], object]
RegisterFontFn = Callable[[object], None]


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


@dataclass(frozen=True, slots=True)
class FontFace:
    name: str
    source_path: Path | None = None


@dataclass(frozen=True, slots=True)
class TextRun:
    text: str
    font_name: str


class FontRegistry:
    """Simple registry around ReportLab font registration."""

    def __init__(self) -> None:
        self._default_font_name = DEFAULT_FONT_NAME
        self._fallback_font_names: list[str] = []
        self._faces: dict[str, FontFace] = {
            DEFAULT_FONT_NAME: FontFace(name=DEFAULT_FONT_NAME, source_path=None)
        }

    def register_ttf(self, name: str, source_path: str | Path, *, set_default: bool = False, fallback: bool = False) -> FontFace:
        path = Path(source_path)
        pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
        ttfonts = import_module("reportlab.pdfbase.ttfonts")
        tt_font_class = cast(TTFontFactory, getattr(ttfonts, "TTFont"))
        register_font = cast(RegisterFontFn, getattr(pdfmetrics, "registerFont"))
        register_font(tt_font_class(name, str(path)))
        face = FontFace(name=name, source_path=path)
        self._faces[name] = face
        if set_default:
            self._default_font_name = name
        if fallback:
            self.add_fallback(name)
        return face

    def get(self, name: str | None = None) -> FontFace:
        resolved_name = name or self._default_font_name
        try:
            return self._faces[resolved_name]
        except KeyError as error:
            raise KeyError(f"Font not registered: {resolved_name}") from error

    def ensure_registered(self, name: str) -> None:
        if name not in self._faces:
            raise KeyError(f"Font not registered: {name}")

    def set_default(self, name: str) -> FontFace:
        face = self.get(name)
        self._default_font_name = face.name
        return face

    def set_fallbacks(self, names: list[str]) -> list[FontFace]:
        faces = [self.get(name) for name in names]
        self._fallback_font_names = [face.name for face in faces]
        return faces

    def add_fallback(self, name: str) -> FontFace:
        face = self.get(name)
        if face.name not in self._fallback_font_names:
            self._fallback_font_names.append(face.name)
        return face

    @property
    def fallback_names(self) -> tuple[str, ...]:
        return tuple(self._fallback_font_names)

    def resolve_text_runs(self, text: str, font_name: str | None = None) -> list[TextRun]:
        resolved_primary = self.get(font_name).name
        runs: list[TextRun] = []
        current_font = ""
        current_text = ""
        for character in text:
            resolved_font = self.font_for_character(character, resolved_primary)
            if resolved_font == current_font:
                current_text += character
                continue
            if current_text:
                runs.append(TextRun(text=current_text, font_name=current_font))
            current_font = resolved_font
            current_text = character
        if current_text:
            runs.append(TextRun(text=current_text, font_name=current_font))
        return runs

    def font_for_character(self, character: str, font_name: str | None = None) -> str:
        resolved_primary = self.get(font_name).name
        for candidate in (resolved_primary, *self._fallback_font_names):
            if self.supports_character(candidate, character):
                return candidate
        return resolved_primary

    def supports_character(self, font_name: str, character: str) -> bool:
        self.ensure_registered(font_name)
        return _font_supports_codepoint(font_name, ord(character))

    def string_width(self, text: str, font_name: str, font_size: float) -> float:
        string_width = _string_width_fn()
        return sum(string_width(run.text, run.font_name, font_size) for run in self.resolve_text_runs(text, font_name))

    @property
    def default_name(self) -> str:
        return self._default_font_name


DEFAULT_FONT_REGISTRY = FontRegistry()


def register_font(name: str, source_path: str | Path, *, set_default: bool = False, fallback: bool = False) -> FontFace:
    return DEFAULT_FONT_REGISTRY.register_ttf(name, source_path, set_default=set_default, fallback=fallback)


def get_font(name: str | None = None) -> FontFace:
    return DEFAULT_FONT_REGISTRY.get(name)


def set_default_font(name: str) -> FontFace:
    return DEFAULT_FONT_REGISTRY.set_default(name)


def set_fallback_fonts(names: list[str]) -> list[FontFace]:
    return DEFAULT_FONT_REGISTRY.set_fallbacks(names)


def add_fallback_font(name: str) -> FontFace:
    return DEFAULT_FONT_REGISTRY.add_fallback(name)


def get_fallback_fonts() -> tuple[str, ...]:
    return DEFAULT_FONT_REGISTRY.fallback_names


def resolve_text_runs(text: str, font_name: str | None = None) -> list[TextRun]:
    return DEFAULT_FONT_REGISTRY.resolve_text_runs(text, font_name)


def string_width(text: str, font_name: str, font_size: float) -> float:
    return DEFAULT_FONT_REGISTRY.string_width(text, font_name, font_size)


def get_default_font_name() -> str:
    return DEFAULT_FONT_REGISTRY.default_name


__all__ = [
    "DEFAULT_FONT_NAME",
    "DEFAULT_FONT_REGISTRY",
    "FontFace",
    "FontRegistry",
    "TextRun",
    "add_fallback_font",
    "get_default_font_name",
    "get_fallback_fonts",
    "get_font",
    "register_font",
    "resolve_text_runs",
    "set_default_font",
    "set_fallback_fonts",
    "string_width",
]


def _string_width_fn() -> StringWidthFn:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    return cast(StringWidthFn, getattr(pdfmetrics, "stringWidth"))


@lru_cache(maxsize=65536)
def _font_supports_codepoint(font_name: str, codepoint: int) -> bool:
    if codepoint in (9, 10, 13, 32):
        return True
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    font = pdfmetrics.getFont(font_name)
    face = getattr(font, "face", None)
    char_to_glyph = getattr(face, "charToGlyph", None)
    if isinstance(char_to_glyph, dict):
        return codepoint in char_to_glyph
    if font_name in {
        "Helvetica",
        "Helvetica-Bold",
        "Helvetica-Oblique",
        "Helvetica-BoldOblique",
        "Times-Roman",
        "Times-Bold",
        "Times-Italic",
        "Times-BoldItalic",
        "Courier",
        "Courier-Bold",
        "Courier-Oblique",
        "Courier-BoldOblique",
    }:
        return 32 <= codepoint <= 255
    return True
