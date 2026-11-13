"""Debug rendering contracts through the public document API."""

from __future__ import annotations

import unittest
import warnings
from io import BytesIO

from pypdf import PdfReader

from smart_report import Canvas, DocumentBuilder, document
from smart_report.render.diagnostics import LayoutOverflowWarning


def _report() -> DocumentBuilder:
    doc = document()
    panel = Canvas().size(120, 60).padding(8).overflow("hidden").name("panel")
    panel.add_text("Body text").name("body")
    doc.page((200, 160)).padding(12).add(panel)
    return doc


class LayoutDiagnosticsTests(unittest.TestCase):
    def test_debug_labels_are_opt_in_and_do_not_change_normal_output(self) -> None:
        doc = _report()
        before = PdfReader(BytesIO(doc.save_to_bytes()))
        debug = PdfReader(BytesIO(doc.save_to_bytes(debug_layout=True)))
        after = PdfReader(BytesIO(doc.save_to_bytes()))

        self.assertEqual(len(debug.pages), len(before.pages))
        self.assertIn("panel [1]", debug.pages[0].extract_text())
        self.assertIn("body [1]", debug.pages[0].extract_text())
        self.assertEqual(before.pages[0].extract_text(), "Body text\n")
        after_stream = after.pages[0].get_contents()
        before_stream = before.pages[0].get_contents()
        debug_stream = debug.pages[0].get_contents()
        assert after_stream is not None and before_stream is not None and debug_stream is not None
        self.assertEqual(after_stream.get_data(), before_stream.get_data())
        operators = debug_stream.get_data()
        self.assertIn(b".1 .35 .9 RG", operators)
        self.assertIn(b"0 .6 .3 RG", operators)
        self.assertIn(b"1 .45 0 RG", operators)

    def test_oversized_node_warning_names_page_and_bounds_only_in_debug_mode(self) -> None:
        doc = document()
        doc.page((200, 160)).padding(0).add_rect().absolute(10, 10).size(100, 200).name("oversized-card")
        with warnings.catch_warnings(record=True) as normal:
            warnings.simplefilter("always")
            doc.save_to_bytes()
        self.assertEqual(normal, [])

        with self.assertWarns(LayoutOverflowWarning) as caught:
            doc.build().save_to_bytes(debug_layout=True)

        self.assertIn("Page 1: 'oversized-card'", str(caught.warning))
        self.assertIn("height=200", str(caught.warning))
        self.assertIn("Reduce the node size", str(caught.warning))
