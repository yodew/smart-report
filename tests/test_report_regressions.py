"""End-to-end report contracts and reviewed raster baselines."""

from __future__ import annotations

import unittest
from io import BytesIO

from pypdf import PdfReader

from examples.quality_reports import chinese_report, rich_table_report

class ReportContentTests(unittest.TestCase):
    def test_chinese_paragraphs_survive_pagination_once_with_page_overlays(self) -> None:
        reader = PdfReader(BytesIO(chinese_report().save_to_bytes()))
        texts = [page.extract_text() for page in reader.pages]
        combined = "".join(texts)
        self.assertEqual(len(texts), 4)
        for index in range(8):
            self.assertEqual(combined.count(f"段落{index + 1:02d}："), 1)
        for index, text in enumerate(texts, start=1):
            self.assertIn("中文报告回归样本", text)
            self.assertIn(f"Page {index}/4", text)

    def test_rich_table_preserves_every_fragment_and_link_across_pages(self) -> None:
        reader = PdfReader(BytesIO(rich_table_report().save_to_bytes()))
        texts = [page.extract_text() for page in reader.pages]
        combined = "".join(texts)
        self.assertGreater(len(texts), 1)
        for row in range(1, 5):
            for part in range(1, 9):
                self.assertEqual(combined.count(f"R{row}P{part}"), 1)
        links = {
            annotation.get_object()["/A"]["/URI"]
            for page in reader.pages
            for annotation in page.get("/Annots", [])
        }
        self.assertEqual(links, {
            f"https://example.com/row/{row}/part/{part}"
            for row in range(1, 5) for part in range(1, 9)
        })
        for text in texts:
            self.assertIn("Details", text)
