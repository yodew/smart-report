"""Font registration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast


DEFAULT_FONT_NAME = "Helvetica"
BASE14_FONT_NAMES = (
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Symbol",
    "ZapfDingbats",
)
TTFontFactory = Callable[[str, str], object]
RegisterFontFn = Callable[[object], None]


class StringWidthFn(Protocol):
    def __call__(self, text: str, font_name: str, font_size: float) -> float: ...


@dataclass(frozen=True, slots=True)
class FontFace:
    name: str
    source_path: Path | None = None
    family_name: str | None = None
    style_name: str | None = None
    codepoints: frozenset[int] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class FontFamily:
    name: str
    regular: str
    bold: str | None = None
    italic: str | None = None
    bold_italic: str | None = None


@dataclass(frozen=True, slots=True)
class TextRun:
    text: str
    font_name: str


class FontRegistry:
    """Simple registry around ReportLab font registration."""

    def __init__(self) -> None:
        self._default_font_name = DEFAULT_FONT_NAME
        self._default_family_name: str | None = None
        self._fallback_font_names: list[str] = []
        self._fallback_family_names: list[str] = []
        self._faces: dict[str, FontFace] = {
            name: FontFace(name=name, source_path=None) for name in BASE14_FONT_NAMES
        }
        self._families: dict[str, FontFamily] = {}

    def register_ttf(self, name: str, source_path: str | Path, *, set_default: bool = False, fallback: bool = False) -> FontFace:
        path = Path(source_path)
        pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
        ttfonts = import_module("reportlab.pdfbase.ttfonts")
        tt_font_class = cast(TTFontFactory, getattr(ttfonts, "TTFont"))
        register_font = cast(RegisterFontFn, getattr(pdfmetrics, "registerFont"))
        register_font(tt_font_class(name, str(path)))
        family_name, style_name, codepoints = _font_metadata(path)
        face = FontFace(name=name, source_path=path, family_name=family_name, style_name=style_name, codepoints=codepoints)
        self._faces[name] = face
        if set_default:
            self._default_font_name = name
        if fallback:
            self.add_fallback(name)
        return face

    def register_family(
        self,
        name: str,
        *,
        regular: str | Path,
        bold: str | Path | None = None,
        italic: str | Path | None = None,
        bold_italic: str | Path | None = None,
        set_default: bool = False,
        fallback: bool = False,
    ) -> FontFamily:
        regular_face = self.register_ttf(name, regular)
        bold_face = self.register_ttf(f"{name}-Bold", bold) if bold is not None else None
        italic_face = self.register_ttf(f"{name}-Italic", italic) if italic is not None else None
        bold_italic_face = self.register_ttf(f"{name}-BoldItalic", bold_italic) if bold_italic is not None else None
        family = FontFamily(
            name=name,
            regular=regular_face.name,
            bold=bold_face.name if bold_face is not None else None,
            italic=italic_face.name if italic_face is not None else None,
            bold_italic=bold_italic_face.name if bold_italic_face is not None else None,
        )
        self._families[name] = family
        if set_default:
            self.set_default_family(name)
        if fallback:
            self.add_fallback_family(name)
        return family

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

    def get_family(self, name: str | None = None) -> FontFamily:
        resolved_name = name or self._default_family_name
        if resolved_name is None:
            raise KeyError("No default font family is registered")
        try:
            return self._families[resolved_name]
        except KeyError as error:
            raise KeyError(f"Font family not registered: {resolved_name}") from error

    def set_default_family(self, name: str) -> FontFamily:
        family = self.get_family(name)
        self._default_family_name = family.name
        self._default_font_name = family.regular
        return family

    def set_fallbacks(self, names: list[str]) -> list[FontFace]:
        faces = [self.get(name) for name in names]
        self._fallback_font_names = [face.name for face in faces]
        return faces

    def add_fallback(self, name: str) -> FontFace:
        face = self.get(name)
        if face.name not in self._fallback_font_names:
            self._fallback_font_names.append(face.name)
        return face

    def set_fallback_families(self, names: list[str]) -> list[FontFamily]:
        families = [self.get_family(name) for name in names]
        self._fallback_family_names = [family.name for family in families]
        self._fallback_font_names = [family.regular for family in families]
        return families

    def add_fallback_family(self, name: str) -> FontFamily:
        family = self.get_family(name)
        if family.name not in self._fallback_family_names:
            self._fallback_family_names.append(family.name)
        if family.regular not in self._fallback_font_names:
            self._fallback_font_names.append(family.regular)
        return family

    @property
    def fallback_names(self) -> tuple[str, ...]:
        return tuple(self._fallback_font_names)

    @property
    def fallback_family_names(self) -> tuple[str, ...]:
        return tuple(self._fallback_family_names)

    def font_name_for_family(self, family_name: str | None, *, bold: bool = False, italic: bool = False) -> str:
        if family_name is None:
            return self._default_font_name
        family = self.get_family(family_name)
        if bold and italic and family.bold_italic is not None:
            return family.bold_italic
        if bold and family.bold is not None:
            return family.bold
        if italic and family.italic is not None:
            return family.italic
        return family.regular

    def resolve_text_runs(self, text: str, font_name: str | None = None) -> list[TextRun]:
        resolved_primary = self.get(font_name).name
        runs: list[TextRun] = []
        current_font = ""
        current_chars: list[str] = []
        for character in text:
            resolved_font = self.font_for_character(character, resolved_primary)
            if resolved_font == current_font:
                current_chars.append(character)
                continue
            if current_chars:
                runs.append(TextRun(text="".join(current_chars), font_name=current_font))
            current_font = resolved_font
            current_chars = [character]
        if current_chars:
            runs.append(TextRun(text="".join(current_chars), font_name=current_font))
        return runs

    def font_for_character(self, character: str, font_name: str | None = None) -> str:
        resolved_primary = self.get(font_name).name
        for candidate in (resolved_primary, *self._fallback_font_names):
            if self.supports_character(candidate, character):
                return candidate
        return resolved_primary

    def supports_character(self, font_name: str, character: str) -> bool:
        self.ensure_registered(font_name)
        face = self._faces[font_name]
        if face.codepoints:
            return ord(character) in face.codepoints
        return _font_supports_codepoint(font_name, ord(character))

    def string_width(self, text: str, font_name: str, font_size: float) -> float:
        string_width = _string_width_fn()
        return sum(string_width(run.text, run.font_name, font_size) for run in self.resolve_text_runs(text, font_name))

    def shaped_string_width(self, text: str, font_name: str, font_size: float) -> float:
        string_width = _string_width_fn()
        total = 0.0
        for run in self.resolve_text_runs(text, font_name):
            face = self.get(run.font_name)
            if face.source_path is None:
                total += string_width(run.text, run.font_name, font_size)
                continue
            total += _harfbuzz_width(run.text, face.source_path, font_size)
        return total

    @property
    def default_name(self) -> str:
        return self._default_font_name


DEFAULT_FONT_REGISTRY = FontRegistry()


def register_font(name: str, source_path: str | Path, *, set_default: bool = False, fallback: bool = False) -> FontFace:
    return DEFAULT_FONT_REGISTRY.register_ttf(name, source_path, set_default=set_default, fallback=fallback)


def register_font_family(
    name: str,
    *,
    regular: str | Path,
    bold: str | Path | None = None,
    italic: str | Path | None = None,
    bold_italic: str | Path | None = None,
    set_default: bool = False,
    fallback: bool = False,
) -> FontFamily:
    return DEFAULT_FONT_REGISTRY.register_family(
        name,
        regular=regular,
        bold=bold,
        italic=italic,
        bold_italic=bold_italic,
        set_default=set_default,
        fallback=fallback,
    )


def get_font(name: str | None = None) -> FontFace:
    return DEFAULT_FONT_REGISTRY.get(name)


def get_font_family(name: str | None = None) -> FontFamily:
    return DEFAULT_FONT_REGISTRY.get_family(name)


def set_default_font(name: str) -> FontFace:
    return DEFAULT_FONT_REGISTRY.set_default(name)


def set_default_font_family(name: str) -> FontFamily:
    return DEFAULT_FONT_REGISTRY.set_default_family(name)


def set_fallback_fonts(names: list[str]) -> list[FontFace]:
    return DEFAULT_FONT_REGISTRY.set_fallbacks(names)


def set_fallback_font_families(names: list[str]) -> list[FontFamily]:
    return DEFAULT_FONT_REGISTRY.set_fallback_families(names)


def add_fallback_font(name: str) -> FontFace:
    return DEFAULT_FONT_REGISTRY.add_fallback(name)


def add_fallback_font_family(name: str) -> FontFamily:
    return DEFAULT_FONT_REGISTRY.add_fallback_family(name)


def get_fallback_fonts() -> tuple[str, ...]:
    return DEFAULT_FONT_REGISTRY.fallback_names


def get_fallback_font_families() -> tuple[str, ...]:
    return DEFAULT_FONT_REGISTRY.fallback_family_names


def resolve_text_runs(text: str, font_name: str | None = None) -> list[TextRun]:
    return DEFAULT_FONT_REGISTRY.resolve_text_runs(text, font_name)


def string_width(text: str, font_name: str, font_size: float) -> float:
    return DEFAULT_FONT_REGISTRY.string_width(text, font_name, font_size)


def shaped_string_width(text: str, font_name: str, font_size: float) -> float:
    return DEFAULT_FONT_REGISTRY.shaped_string_width(text, font_name, font_size)


def get_default_font_name() -> str:
    return DEFAULT_FONT_REGISTRY.default_name


__all__ = [
    "BASE14_FONT_NAMES",
    "DEFAULT_FONT_NAME",
    "DEFAULT_FONT_REGISTRY",
    "FontFace",
    "FontFamily",
    "FontRegistry",
    "TextRun",
    "add_fallback_font",
    "add_fallback_font_family",
    "get_default_font_name",
    "get_fallback_font_families",
    "get_fallback_fonts",
    "get_font",
    "get_font_family",
    "register_font",
    "register_font_family",
    "resolve_text_runs",
    "set_default_font",
    "set_default_font_family",
    "set_fallback_font_families",
    "set_fallback_fonts",
    "shaped_string_width",
    "string_width",
]


def _string_width_fn() -> StringWidthFn:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    return cast(StringWidthFn, getattr(pdfmetrics, "stringWidth"))


def _font_metadata(path: Path) -> tuple[str | None, str | None, frozenset[int]]:
    tt_lib = import_module("fontTools.ttLib")
    tt_font_class = getattr(tt_lib, "TTFont")
    font = tt_font_class(str(path))
    try:
        cmap = font.getBestCmap()
        family_name = None
        style_name = None
        name_table = font["name"] if "name" in font else None
        if name_table is not None:
            family_name = _name_record(name_table, 1)
            style_name = _name_record(name_table, 2)
        return family_name, style_name, frozenset(cmap.keys())
    finally:
        close = getattr(font, "close", None)
        if callable(close):
            close()


def _name_record(name_table: object, name_id: int) -> str | None:
    get_name = getattr(name_table, "getName")
    record = get_name(name_id, 3, 1, 0x409) or get_name(name_id, 1, 0, 0)
    if record is None:
        return None
    to_unicode = getattr(record, "toUnicode")
    return str(to_unicode())


@lru_cache(maxsize=2048)
def _harfbuzz_width(text: str, source_path: Path, font_size: float) -> float:
    if not text:
        return 0.0
    hb = import_module("uharfbuzz")
    blob_class = getattr(hb, "Blob")
    face_class = getattr(hb, "Face")
    font_class = getattr(hb, "Font")
    buffer_class = getattr(hb, "Buffer")
    shape = getattr(hb, "shape")

    blob = blob_class.from_file_path(str(source_path))
    face = face_class(blob)
    font = font_class(face)
    buffer = buffer_class()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    shape(font, buffer, {"kern": True, "liga": True, "clig": True, "calt": True})
    scale = font_size / float(face.upem or 1000)
    return sum(float(position.x_advance) * scale for position in buffer.glyph_positions)


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
