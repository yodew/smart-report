"""PDF-level contracts for optional Gaussian text shadows."""

from __future__ import annotations

import math
import sys
from collections.abc import Iterator
from contextlib import closing
from importlib.util import find_spec
from io import BytesIO
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from typing_extensions import Unpack
import unittest
from unittest.mock import patch

if find_spec("pypdf") is None or find_spec("pypdfium2") is None:
    raise unittest.SkipTest("PDF shadow tests require pypdf and smart-report[gaussian]")

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream, DictionaryObject, StreamObject
from pypdfium2 import PdfDocument

from smart_report import RichText, Text, document
from smart_report.render.gaussian_shadow import (
    GaussianShadowDependencyError,
    ShadowRasterLimitError,
)


class ShadowOptions(TypedDict, total=False):
    method: Literal["stroke", "gaussian"]
    sigma: float
    dpi: float
    blur: float
    color: str
    x: float
    y: float
    knockout: bool


def _pdf(rich: bool = False, **shadow: Unpack[ShadowOptions]) -> bytes:
    doc = document()
    page = doc.page((300, 160)).padding(0)
    node = (
        RichText().span("Shadow", font_size=26).br().span("Second", font_size=18)
        if rich
        else Text("Shadow\nSecond").font_size(26)
    )
    node.absolute(40, 35).size(220, 100).align("center").line_height(32)
    node.text_shadow(**shadow)
    page.add(node)
    return doc.save_to_bytes()


def _bitmap(data: bytes) -> Image.Image:
    with (
        closing(PdfDocument(data)) as pdf,
        closing(pdf[0]) as page,
        closing(page.render(scale=2, fill_color=(0, 0, 0, 0))) as bitmap,
    ):
        return bitmap.to_pil().convert("RGBA")


def _pixels(image: Image.Image) -> Iterator[tuple[int, int, int, int]]:
    data = image.tobytes()
    return zip(data[0::4], data[1::4], data[2::4], data[3::4], strict=True)


class GaussianShadowTests(unittest.TestCase):
    def test_gaussian_pdf_preserves_text_and_soft_alpha_for_plain_and_rich(
        self,
    ) -> None:
        for rich in (False, True):
            with self.subTest(rich=rich):
                data = _pdf(
                    rich, method="gaussian", sigma=3, dpi=300, color="#ff000080"
                )
                reader = PdfReader(BytesIO(data))
                self.assertEqual(
                    "".join(reader.pages[0].extract_text().split()), "ShadowSecond"
                )
                resources = reader.pages[0]["/Resources"]
                assert isinstance(resources, DictionaryObject)
                xobjects = resources["/XObject"]
                assert isinstance(xobjects, DictionaryObject)
                images = list(xobjects.values())
                self.assertEqual(len(images), 1)
                image = images[0].get_object()
                assert isinstance(image, StreamObject)
                mask = image["/SMask"].get_object()
                assert isinstance(mask, StreamObject)
                samples = mask.get_data()
                control = PdfReader(
                    BytesIO(
                        _pdf(rich, method="gaussian", sigma=3, dpi=300, color="#ff0000")
                    )
                )
                control_image = control.pages[0].images[0].image
                assert control_image is not None
                expected = bytes(
                    round(a * 128 / 255)
                    for a in control_image.getchannel("A").tobytes()
                )
                self.assertEqual(samples, expected)
                self.assertGreater(len(set(samples)), 30)
                self.assertLessEqual(max(samples), 128)
                self.assertEqual(samples[0], 0)
                self.assertEqual(samples[-1], 0)

    def test_sigma_increases_visible_halo_without_repositioning_foreground(
        self,
    ) -> None:
        narrow = _bitmap(_pdf(method="gaussian", sigma=1, dpi=288, color="#ff0000"))
        wide = _bitmap(_pdf(method="gaussian", sigma=5, dpi=288, color="#ff0000"))
        narrow_halo = sum(r > 200 and a > 2 for r, g, b, a in _pixels(narrow))
        wide_halo = sum(r > 200 and a > 2 for r, g, b, a in _pixels(wide))
        self.assertGreater(wide_halo, narrow_halo * 1.5)
        # The opaque black foreground remains at exactly the same pixels.
        foreground = lambda image: {
            (i, p) for i, p in enumerate(_pixels(image)) if p[0] == 0 and p[3] == 255
        }
        self.assertEqual(foreground(narrow), foreground(wide))

    def test_knockout_removes_glyph_interior_but_keeps_external_halo(self) -> None:
        masks = []
        for knockout in (False, True):
            reader = PdfReader(
                BytesIO(_pdf(method="gaussian", sigma=2, dpi=288, knockout=knockout))
            )
            image = reader.pages[0].images[0].image
            self.assertIsNotNone(image)
            if image is not None:
                masks.append(list(image.getchannel("A").tobytes()))
        self.assertLess(sum(masks[1]), sum(masks[0]) * 0.7)
        self.assertGreater(sum(masks[1]), 0)

    def test_knockout_uses_foreground_position_with_signed_offsets_and_zero_sigma(
        self,
    ) -> None:
        for rich in (False, True):
            for x, y in ((80, 20), (-80, -20), (12, 5), (-12, -5)):
                with self.subTest(rich=rich, x=x, y=y):
                    visible = []
                    for knockout in (False, True):
                        doc = document()
                        page = doc.page((300, 160)).padding(0)
                        node = (
                            RichText().span("H", font_size=60)
                            if rich
                            else Text("H").font_size(60)
                        )
                        node.absolute(110, 50).size(100, 80).line_height(72).color(
                            "#000000"
                        )
                        node.text_shadow(
                            method="gaussian",
                            sigma=0,
                            dpi=288,
                            x=x,
                            y=y,
                            knockout=knockout,
                            color="#ff0000",
                        )
                        page.add(node)
                        image = _bitmap(doc.save_to_bytes())
                        visible.append(
                            {
                                i
                                for i, pixel in enumerate(_pixels(image))
                                if pixel == (255, 0, 0, 255)
                            }
                        )
                    # Opaque foreground already covers its interior: knockout must preserve
                    # the same solid external shadow, allowing only antialias-edge differences.
                    self.assertTrue(visible[0])
                    self.assertGreaterEqual(
                        len(visible[0] & visible[1]), len(visible[0]) * 0.9
                    )

    def test_legacy_shadow_does_not_leak_stroke_mode_into_foreground(self) -> None:
        for rich in (False, True):
            with self.subTest(rich=rich):
                reader = PdfReader(BytesIO(_pdf(rich, blur=6, color="#ff0000")))
                mode = 0
                stack: list[int] = []
                modes: list[int] = []
                for operands, operator in ContentStream(
                    reader.pages[0].get_contents(), reader
                ).operations:
                    if operator == b"q":
                        stack.append(mode)
                    elif operator == b"Q":
                        mode = stack.pop()
                    elif operator == b"Tr":
                        mode = int(operands[0])
                    elif operator in (b"Tj", b"TJ"):
                        modes.append(mode)
                self.assertEqual(modes, [2, 2, 0, 0])

    def test_shadow_offset_moves_only_shadow(self) -> None:
        for rich in (False, True):
            with self.subTest(rich=rich):
                translations = []
                for x, y in ((0, 0), (10, -5)):
                    reader = PdfReader(
                        BytesIO(
                            _pdf(rich, method="gaussian", sigma=2, dpi=288, x=x, y=y)
                        )
                    )
                    matrices = [
                        tuple(float(v) for v in args)
                        for args, op in ContentStream(
                            reader.pages[0].get_contents(), reader
                        ).operations
                        if op == b"cm" and float(args[0]) > 1
                    ]
                    self.assertEqual(len(matrices), 1)
                    translations.append(matrices[0][-2:])
                self.assertAlmostEqual(
                    translations[1][0] - translations[0][0], 10, delta=0.01
                )
                self.assertAlmostEqual(
                    translations[1][1] - translations[0][1], 5, delta=0.01
                )

    def test_missing_optional_dependency_is_explicit(self) -> None:
        with patch.dict(sys.modules, {"pypdfium2": None}):
            # The default mode remains usable without PDFium.
            self.assertIn(b"%PDF", _pdf(blur=2))
            with self.assertRaises(GaussianShadowDependencyError):
                _pdf(method="gaussian", sigma=3)

    def test_invalid_parameters_are_rejected_at_builder_boundary(self) -> None:
        cases: tuple[ShadowOptions, ...] = (
            {"method": "gaussian"},
            {"method": "gaussian", "sigma": -1},
            {"method": "gaussian", "sigma": math.nan},
            {"method": "gaussian", "sigma": 2, "blur": 3},
            {"sigma": 2},
            {"dpi": 0},
            {"dpi": math.inf},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Text("test").text_shadow(
                    method=kwargs.get("method", "stroke"),
                    sigma=kwargs.get("sigma"),
                    dpi=kwargs.get("dpi", 300),
                    blur=kwargs.get("blur", 0),
                )

    def test_oversized_shadow_is_rejected_before_bitmap_allocation(self) -> None:
        with self.assertRaises(ShadowRasterLimitError):
            _pdf(method="gaussian", sigma=1e308)


if __name__ == "__main__":
    unittest.main()
