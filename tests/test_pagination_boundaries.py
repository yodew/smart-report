"""Atomic overflow contracts through the public PDF rendering API."""

from __future__ import annotations

import os
import unittest
import warnings
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream
from typing_extensions import assert_never

from examples.pagination_boundaries import BoundaryCase, boundary_report
from smart_report import Canvas, LayoutOverflowWarning, document

CASES: tuple[BoundaryCase, ...] = ("image", "rowspan", "complex")


def _save_case(case: BoundaryCase, height: float, intro: bool = False) -> tuple[PdfReader, list[LayoutOverflowWarning]]:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", LayoutOverflowWarning)
        data = boundary_report(case, height, intro=intro).save_to_bytes(debug_layout=True)
    output = os.environ.get("SMART_REPORT_QA_DIR")
    if output:
        path = Path(output)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"boundary-{case}-{height:g}.pdf").write_bytes(data)
    issues = [entry.message for entry in captured if isinstance(entry.message, LayoutOverflowWarning)]
    return PdfReader(BytesIO(data)), issues


class PaginationBoundaryTests(unittest.TestCase):
    def _assert_payload(self, reader: PdfReader, case: BoundaryCase, height: float) -> None:
        text = "".join(page.extract_text() for page in reader.pages)
        match case:
            case "image":
                transforms = [
                    tuple(float(value) for value in args)
                    for page in reader.pages
                    for args, op in ContentStream(page.get_contents(), reader).operations
                    if op == b"cm" and float(args[0]) == 80
                ]
                self.assertEqual(len(transforms), 1)
                self.assertEqual(transforms[0][3], height)
            case "rowspan":
                for token in ("MERGED", "ROW-A", "ROW-B"):
                    self.assertEqual(text.count(token), 1)
            case "complex":
                for token in ("CELL", "LEFT", "RIGHT"):
                    self.assertEqual(text.count(token), 1)
            case unreachable:
                assert_never(unreachable)

    def test_absolute_region_and_descendants_can_use_page_padding(self) -> None:
        doc = document()
        layer = Canvas().absolute(-20, -20).size(160, 40)
        layer.add_text("Absolute region").width(150)
        doc.page((240, 180)).padding(30).add(layer)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", LayoutOverflowWarning)
            doc.save_to_bytes(debug_layout=True)
        self.assertEqual(captured, [])

    def test_atomic_content_moves_once_when_a_fresh_body_can_fit_it(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                reader, issues = _save_case(case, 80, intro=True)
                self.assertEqual(len(reader.pages), 2)
                self.assertEqual(issues, [])
                self.assertIn("INTRO", reader.pages[0].extract_text())
                self.assertNotIn(f"atomic-{case}", reader.pages[0].extract_text())
                self.assertIn(f"atomic-{case}", reader.pages[1].extract_text())
                self._assert_payload(reader, case, 80)

    def test_atomic_content_too_tall_for_body_preserves_size_and_warns(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                reader, issues = _save_case(case, 140)
                self.assertEqual(len(reader.pages), 1)
                named = [issue for issue in issues if issue.node_name == f"atomic-{case}"]
                self.assertEqual(len(named), 1)
                self.assertEqual(named[0].bounds.height, 140)
                self.assertIn("page body", str(named[0]))
                self.assertEqual(reader.pages[0].extract_text().count(f"atomic-{case}"), 1)
                self._assert_payload(reader, case, 140)

    def test_atomic_content_taller_than_physical_page_does_not_loop_or_slice(self) -> None:
        for case in CASES:
            with self.subTest(case=case):
                reader, issues = _save_case(case, 220)
                self.assertEqual(len(reader.pages), 1)
                named = [issue for issue in issues if issue.node_name == f"atomic-{case}"]
                self.assertEqual(len(named), 1)
                self.assertEqual(named[0].bounds.height, 220)
                self.assertIn("physical page", str(named[0]))
                self._assert_payload(reader, case, 220)
