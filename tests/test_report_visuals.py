"""Reviewed PDF raster contracts; the full environment must execute these."""

from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import closing
from importlib.util import find_spec
from pathlib import Path

from PIL import Image, ImageChops

if find_spec("pypdfium2") is None:
    raise unittest.SkipTest("Report raster tests require smart-report[gaussian]")

from examples.quality_reports import chinese_report, rich_table_report

FIXTURES = Path(__file__).parent / "fixtures/quality"


class ReportRasterTests(unittest.TestCase):
    def test_reports_match_reviewed_page_images(self) -> None:
        from pypdfium2 import PdfDocument
        from examples.yuanxi_text_effects import main as yuanxi_report

        with tempfile.TemporaryDirectory() as directory:
            output = Path(os.environ.get("SMART_REPORT_QA_DIR", directory))
            output.mkdir(parents=True, exist_ok=True)
            (output / "chinese.pdf").write_bytes(chinese_report().save_to_bytes())
            (output / "rich-table.pdf").write_bytes(rich_table_report().save_to_bytes())
            yuanxi_report(output / "yuanxi.pdf")
            for name in ("chinese", "rich-table", "yuanxi"):
                with closing(PdfDocument(output / f"{name}.pdf")) as pdf:
                    expected = sorted(FIXTURES.glob(f"{name}-*.png"))
                    self.assertEqual(len(pdf), len(expected), name)
                    for index, baseline_path in enumerate(expected):
                        with self.subTest(report=name, page=index + 1):
                            with closing(pdf[index]) as page, closing(page.render(scale=1)) as bitmap:
                                actual = bitmap.to_pil().convert("RGB")
                            actual.save(output / baseline_path.name)
                            with Image.open(baseline_path) as baseline:
                                self.assertEqual(actual.size, baseline.size)
                                difference = ImageChops.difference(actual, baseline.convert("RGB"))
                            # Ignore small antialias differences; flag visibly changed pixels.
                            changed = sum(value > 24 for value in difference.tobytes())
                            changed_fraction = changed / (actual.width * actual.height * 3)
                            if changed_fraction > 0.001:
                                difference.save(output / f"{baseline_path.stem}-diff.png")
                            self.assertLessEqual(changed_fraction, 0.001)
