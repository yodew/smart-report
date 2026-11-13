"""PDF coordinate contracts that text extraction alone cannot verify."""

from __future__ import annotations

import unittest
from io import BytesIO

from pypdf import PdfReader

from examples.quality_reports import rich_table_report
from smart_report import document


def _text_baselines(data: bytes) -> list[tuple[int, str, float]]:
    positions: list[tuple[int, str, float]] = []
    for index, page in enumerate(PdfReader(BytesIO(data)).pages):
        page.extract_text(visitor_text=lambda text, cm, tm, _font, _size: positions.append(
            (index, text.strip(), tm[4] * cm[1] + tm[5] * cm[3] + cm[5])
        ) if text.strip() else None)
    return positions


class PageGeometryTests(unittest.TestCase):
    def test_footer_is_inside_physical_page_with_padding(self) -> None:
        doc = document()
        doc.header().height(20).add_text("Header").font_size(10)
        doc.footer().height(20).add_text("Footer").font_size(10)
        doc.page((200, 160)).padding(24).add_text("Body").font_size(10)

        positions = {text: y for _page, text, y in _text_baselines(doc.save_to_bytes())}

        self.assertEqual(positions["Header"], 150)
        self.assertEqual(positions["Footer"], 10)
        self.assertEqual(positions["Body"], 126)

    def test_continued_table_text_stays_above_bottom_page_padding(self) -> None:
        positions = _text_baselines(rich_table_report().save_to_bytes())

        for page, text, y in positions:
            with self.subTest(page=page + 1, text=text):
                self.assertGreaterEqual(y, 20)
