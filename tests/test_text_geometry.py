"""Compare emitted PDF advances with alignment and clickable text regions."""

from __future__ import annotations

import os
import unittest
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PageObject, PdfReader
from pypdf.generic import ArrayObject, ByteStringObject, ContentStream, DictionaryObject, NumberObject, TextStringObject

from smart_report import (
    DocumentBuilder, Frame, RichText, document, get_fallback_fonts,
    register_font, set_fallback_fonts,
)


@dataclass(frozen=True, slots=True)
class Glyph:
    x: float
    y: float
    width: float
    font: str


def _glyphs(page: PageObject) -> list[Glyph]:
    """Read horizontal Tj advances from embedded PDF widths, independently of layout.

    Fixtures use translation-only text matrices, embedded TrueType subsets and no
    word spacing. Char spacing advances the cursor after every glyph, including
    across Tj/font boundaries; the visible line end excludes its final spacing.
    """
    resources = page["/Resources"]
    assert isinstance(resources, DictionaryObject)
    fonts = resources["/Font"]
    assert isinstance(fonts, DictionaryObject)
    x = y = line_x = leading = spacing = 0.0
    size = 12.0
    font_key = ""
    result: list[Glyph] = []
    for args, op in ContentStream(page.get_contents(), page.pdf).operations:
        match op:
            case b"cm":
                assert [float(value) for value in args] == [1, 0, 0, 1, 0, 0]
            case b"Tm":
                assert [float(value) for value in args[:4]] == [1, 0, 0, 1]
                x, y = float(args[4]), float(args[5])
                line_x = x
            case b"Tf":
                font_key, size = str(args[0]), float(args[1])
            case b"Tc":
                spacing = float(args[0])
            case b"TL":
                leading = float(args[0])
            case b"T*":
                x, y = line_x, y - leading
            case b"Tj":
                raw = args[0]
                match raw:
                    case ByteStringObject():
                        payload = bytes(raw)
                    case TextStringObject():
                        payload = raw.original_bytes
                    case _:
                        raise AssertionError("Expected a PDF text string")
                font = fonts[font_key].get_object()
                assert isinstance(font, DictionaryObject)
                widths = font["/Widths"]
                assert isinstance(widths, ArrayObject)
                first_char = font["/FirstChar"]
                assert isinstance(first_char, NumberObject)
                first = int(first_char)
                for code in payload:
                    advance = float(widths[code - first]) * size / 1000
                    result.append(Glyph(x, y, advance, font_key))
                    x += advance + spacing
            case b"TJ" | b"Td" | b"TD" | b"Tw" | b"Tz" | b"'" | b'"':
                raise AssertionError(f"Extend the fixture reader for {op!r}")
    return result


def _pdf(doc: DocumentBuilder, label: str) -> PdfReader:
    data = doc.save_to_bytes()
    output = os.environ.get("SMART_REPORT_QA_DIR")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"text-geometry-{label}.pdf").write_bytes(data)
    return PdfReader(BytesIO(data))


class TextGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fonts = Path(__file__).resolve().parents[1] / "examples/fonts"
        register_font("GeometrySans", fonts / "SourceHanSansSC-Normal.ttf")
        register_font("GeometryArabic", fonts / "NotoNaskhArabic-Medium.ttf")

    def _assert_link_covers_glyphs(self, page: PageObject) -> list[Glyph]:
        glyphs = _glyphs(page)
        self.assertTrue(glyphs)
        links = [annotation.get_object() for annotation in page.get("/Annots", [])]
        self.assertEqual(len(links), 1)
        left, bottom, right, top = map(float, links[0]["/Rect"])
        self.assertAlmostEqual(left, glyphs[0].x, delta=0.002)
        self.assertAlmostEqual(right, glyphs[-1].x + glyphs[-1].width, delta=0.002)
        for glyph in glyphs:
            self.assertLessEqual(bottom, glyph.y)
            self.assertGreaterEqual(top, glyph.y)
        return glyphs

    def test_plain_mixed_text_alignment_indent_and_spacing_match_pdf_advances(self) -> None:
        for align in ("left", "center", "right"):
            for spacing in (-0.5, 0, 2):
                with self.subTest(align=align, spacing=spacing):
                    doc = document()
                    doc.page((300, 160)).padding(0).add_text("AV中文fi") \
                        .font("GeometrySans").font_size(14).absolute(30, 20).width(220) \
                        .align(align).text_indent(28).letter_spacing(spacing).link("https://example.com/plain")
                    glyphs = self._assert_link_covers_glyphs(_pdf(doc, f"{align}-{spacing}").pages[0])
                    width = glyphs[-1].x + glyphs[-1].width - glyphs[0].x
                    remaining = 220 - 28 - width
                    offset = {"left": 0.0, "center": remaining / 2, "right": remaining}[align]
                    self.assertAlmostEqual(glyphs[0].x, 30 + 28 + offset, delta=0.002)

    def test_fallback_font_switches_preserve_spaced_link_geometry(self) -> None:
        original = list(get_fallback_fonts())
        self.addCleanup(set_fallback_fonts, original)
        set_fallback_fonts(["GeometrySans"])
        doc = document()
        doc.page((300, 160)).padding(0).add_text("A中文B") \
            .font("GeometryArabic").font_size(14).absolute(30, 20).width(220) \
            .align("center").letter_spacing(2).link("https://example.com/fallback")

        page = _pdf(doc, "fallback").pages[0]
        glyphs = self._assert_link_covers_glyphs(page)

        self.assertEqual(len({glyph.font for glyph in glyphs}), 2)
        self.assertEqual("".join(page.extract_text().split()), "A中文B")

    def test_auto_arabic_right_edge_and_link_match_pdf_advances(self) -> None:
        doc = document()
        doc.page((300, 160)).padding(0).add_text("مرحبا") \
            .font("GeometryArabic").font_size(18).absolute(30, 20).width(220) \
            .typography("auto").text_direction("rtl").link("https://example.com/arabic")

        glyphs = self._assert_link_covers_glyphs(_pdf(doc, "arabic-auto").pages[0])

        self.assertAlmostEqual(glyphs[-1].x + glyphs[-1].width, 250, delta=0.002)

    def test_paginated_rich_spans_keep_link_edges_and_continuation_indent(self) -> None:
        doc = document()
        frame = Frame()
        doc.page((150, 100)).padding(10).add(frame)
        rich = RichText().font("GeometrySans").font_size(12).line_height(18) \
            .text_indent(24).align("center").letter_spacing(1)
        rich.span("中文 AV fi " * 8, link="https://example.com/rich")
        rich.span("Mixed 中文 " * 8, font_size=15, letter_spacing=2, link="https://example.com/rich")
        frame.add(rich)

        reader = _pdf(doc, "rich-pagination")

        self.assertGreater(len(reader.pages), 1)
        for page_number, page in enumerate(reader.pages):
            by_baseline: dict[float, list[Glyph]] = {}
            for glyph in _glyphs(page):
                by_baseline.setdefault(round(glyph.y, 3), []).append(glyph)
            links = [annotation.get_object()["/Rect"] for annotation in page.get("/Annots", [])]
            self.assertEqual(len(links), len(by_baseline))
            for line_number, (glyphs, rect) in enumerate(zip(by_baseline.values(), links)):
                with self.subTest(page=page_number + 1, line=line_number + 1):
                    left, bottom, right, top = map(float, rect)
                    self.assertAlmostEqual(left, glyphs[0].x, delta=0.002)
                    self.assertAlmostEqual(right, glyphs[-1].x + glyphs[-1].width, delta=0.002)
                    self.assertLessEqual(bottom, glyphs[0].y)
                    self.assertGreaterEqual(top, glyphs[0].y)
                    indent = 24 if page_number == 0 and line_number == 0 else 0
                    self.assertAlmostEqual(left - (10 + indent), 140 - right, delta=0.002)
