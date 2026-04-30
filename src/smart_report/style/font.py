"""Font registration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, cast


DEFAULT_FONT_NAME = "Helvetica"
TTFontFactory = Callable[[str, str], object]
RegisterFontFn = Callable[[object], None]


@dataclass(frozen=True, slots=True)
class FontFace:
    name: str
    source_path: Path | None = None


class FontRegistry:
    """Simple registry around ReportLab font registration."""

    def __init__(self) -> None:
        self._faces: dict[str, FontFace] = {
            DEFAULT_FONT_NAME: FontFace(name=DEFAULT_FONT_NAME, source_path=None)
        }

    def register_ttf(self, name: str, source_path: str | Path) -> FontFace:
        path = Path(source_path)
        pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
        ttfonts = import_module("reportlab.pdfbase.ttfonts")
        tt_font_class = cast(TTFontFactory, getattr(ttfonts, "TTFont"))
        register_font = cast(RegisterFontFn, getattr(pdfmetrics, "registerFont"))
        register_font(tt_font_class(name, str(path)))
        face = FontFace(name=name, source_path=path)
        self._faces[name] = face
        return face

    def get(self, name: str | None = None) -> FontFace:
        resolved_name = name or DEFAULT_FONT_NAME
        try:
            return self._faces[resolved_name]
        except KeyError as error:
            raise KeyError(f"Font not registered: {resolved_name}") from error

    def ensure_registered(self, name: str) -> None:
        if name not in self._faces:
            raise KeyError(f"Font not registered: {name}")


DEFAULT_FONT_REGISTRY = FontRegistry()
