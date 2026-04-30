"""Regression tests for Table v2."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import cast

from smart_report import Frame, Table, document
from smart_report.layout.paginate import _split_table_node
from smart_report.layout.table_model import table_cell_boxes, table_cell_padding, table_column_widths, table_height

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


class TableV2ModelTests(unittest.TestCase):
    def test_column_widths_support_fixed_percent_and_auto(self) -> None:
        table = Table([["A", "B", "C"]]).column_widths([80, "50%", "auto"])
        table.node.resolved_width = 300
        self.assertEqual(table_column_widths(table.node, 300, 3), [80.0, 150.0, 70.0])

    def test_column_widths_scale_down_when_overflowing(self) -> None:
        table = Table([["A", "B"]]).column_widths([240, 240])
        table.node.resolved_width = 300
        self.assertEqual(table_column_widths(table.node, 300, 2), [150.0, 150.0])

    def test_cell_boxes_apply_alignment_padding_header_and_zebra(self) -> None:
        table = (
            Table([["H1", "H2", "H3"], ["left", "center", "right"], ["odd", "odd", "odd"]])
            .column_widths([100, 100, 100])
            .align(["left", "center", "right"])
            .cell_padding(vertical=8, horizontal=10)
            .header(background="#111827", color="#ffffff")
            .zebra("#f8fafc")
            .font_size(10)
            .line_height(12)
            .background("#ffffff")
            .color("#111827")
        )
        table.node.resolved_width = 300

        padding = table_cell_padding(table.node)
        self.assertEqual((padding.top, padding.right, padding.bottom, padding.left), (8.0, 10.0, 8.0, 10.0))

        boxes = table_cell_boxes(table.node, 0, 0, 300, table_height(table.node))
        self.assertEqual(len(boxes), 9)
        self.assertEqual([boxes[index].align for index in range(3)], ["left", "center", "right"])
        self.assertIsNotNone(boxes[0].background)
        self.assertIsNotNone(boxes[0].color)
        self.assertIsNotNone(boxes[6].background)

    def test_row_column_and_cell_styles_follow_precedence(self) -> None:
        table = (
            Table([["H1", "H2"], ["A", "B"], ["C", "D"]])
            .column_widths([120, 120])
            .header(background="#1d4ed8", color="#ffffff")
            .column_style(1, color="#166534", align="right")
            .row_style(1, background="#ecfeff", color="#0f172a")
            .cell_style(1, 1, background="#dcfce7", color="#166534", align="center")
            .background("#ffffff")
            .color("#111827")
        )
        table.node.resolved_width = 240

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        target = next(box for box in boxes if box.source_row_index == 1 and box.column_index == 1)
        self.assertEqual(target.align, "center")
        self.assertIsNotNone(target.background)
        self.assertIsNotNone(target.color)

    def test_header_style_can_override_font_metrics(self) -> None:
        table = (
            Table([["Header", "Column"], ["A", "B"]])
            .column_widths([120, 120])
            .font("Helvetica")
            .font_size(10)
            .line_height(12)
            .align(["left", "right"])
            .header(background="#1d4ed8", color="#ffffff")
            .header_style(font="Helvetica-Bold", font_size=14, line_height=18, align="center")
        )
        table.node.resolved_width = 240

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        header_box = next(box for box in boxes if box.row_index == 0 and box.column_index == 0)
        header_second_box = next(box for box in boxes if box.row_index == 0 and box.column_index == 1)
        body_box = next(box for box in boxes if box.row_index == 1 and box.column_index == 0)
        body_second_box = next(box for box in boxes if box.row_index == 1 and box.column_index == 1)
        self.assertEqual(header_box.font_name, "Helvetica-Bold")
        self.assertEqual(header_box.font_size, 14)
        self.assertEqual(header_box.line_height, 18)
        self.assertEqual(header_box.align, "center")
        self.assertEqual(header_second_box.align, "center")
        self.assertEqual(body_box.font_name, "Helvetica")
        self.assertEqual(body_box.font_size, 10)
        self.assertEqual(body_box.line_height, 12)
        self.assertEqual(body_second_box.align, "right")
        self.assertGreater(header_box.height, body_box.height)

    def test_header_padding_can_differ_from_body_padding(self) -> None:
        table = (
            Table([["Header", "Column"], ["A", "B"]])
            .column_widths([120, 120])
            .cell_padding(vertical=4, horizontal=6)
            .header_padding(vertical=10, horizontal=12)
            .font_size(10)
            .line_height(12)
        )
        table.node.resolved_width = 240

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        header_box = next(box for box in boxes if box.row_index == 0 and box.column_index == 0)
        body_box = next(box for box in boxes if box.row_index == 1 and box.column_index == 0)
        self.assertEqual((header_box.padding.top, header_box.padding.left), (10, 12))
        self.assertEqual((body_box.padding.top, body_box.padding.left), (4, 6))
        self.assertGreater(header_box.height, body_box.height)

    def test_invalid_alignment_raises(self) -> None:
        table = Table([["A"]]).align("justify")
        table.node.resolved_width = 100
        with self.assertRaises(ValueError):
            _ = table_cell_boxes(table.node, 0, 0, 100, table_height(table.node))


class TableV2PaginationTests(unittest.TestCase):
    def _rows(self, count: int = 18) -> list[list[str]]:
        return [["Region", "Revenue", "Growth"]] + [
            [f"Region {index}", f"${index}", f"+{index}%"] for index in range(1, count)
        ]

    def test_repeat_header_true_repeats_header_in_each_slice(self) -> None:
        table = (
            Table(self._rows())
            .column_widths(["45%", "30%", "25%"])
            .align(["left", "right", "right"])
            .cell_padding(vertical=7, horizontal=9)
            .header(background="#0f172a", color="#ffffff", repeat=True)
            .font_size(10)
            .line_height(13)
        )
        table.node.resolved_width = 420
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 125, 125)
        self.assertGreater(len(slices), 1)
        for table_slice in slices:
            slice_rows = cast(list[list[str]], table_slice.content["rows"])
            slice_header_rows = cast(int, table_slice.content["header_rows"])
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            self.assertEqual(slice_rows[0], self._rows()[0])
            self.assertEqual(slice_header_rows, 1)
            self.assertEqual(slice_source_rows[0], 0)
            self.assertAlmostEqual(table_slice.resolved_height, table_height(table_slice), places=2)

    def test_repeat_header_false_keeps_header_style_only_on_first_slice(self) -> None:
        table = (
            Table(self._rows())
            .column_widths(["45%", "30%", "25%"])
            .header(background="#0f172a", color="#ffffff", repeat=False)
            .font_size(10)
            .line_height(13)
        )
        table.node.resolved_width = 420
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 125, 125)
        self.assertGreater(len(slices), 1)
        first_rows = cast(list[list[str]], slices[0].content["rows"])
        first_header_rows = cast(int, slices[0].content["header_rows"])
        self.assertEqual(first_header_rows, 1)
        self.assertEqual(first_rows[0], self._rows()[0])
        self.assertTrue(all(cast(int, table_slice.content["header_rows"]) == 0 for table_slice in slices[1:]))
        self.assertTrue(all(cast(list[list[str]], table_slice.content["rows"])[0] != self._rows()[0] for table_slice in slices[1:]))

    def test_cell_style_uses_logical_row_indices_after_pagination(self) -> None:
        rows = self._rows(24)
        table = (
            Table(rows)
            .column_widths(["45%", "30%", "25%"])
            .header(background="#0f172a", color="#ffffff", repeat=True)
            .cell_style(10, 1, background="#dcfce7", color="#166534", align="center")
            .font_size(10)
            .line_height(13)
        )
        table.node.resolved_width = 420
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 125, 125)
        matched_boxes = []
        for table_slice in slices:
            boxes = table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
            matched_boxes.extend([box for box in boxes if box.source_row_index == 10 and box.column_index == 1])

        self.assertEqual(len(matched_boxes), 1)
        self.assertEqual(matched_boxes[0].align, "center")
        self.assertIsNotNone(matched_boxes[0].background)


@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class TableV2PdfTests(unittest.TestCase):
    def test_repeat_header_pdf_output(self) -> None:
        assert PdfReader is not None
        rows = [["Region", "Revenue", "Growth"]] + [
            [f"Region {index}", f"${index * 100}K", f"+{(index % 8) + 3}%"] for index in range(1, 80)
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            true_path = Path(tmp_dir) / "repeat_true.pdf"
            false_path = Path(tmp_dir) / "repeat_false.pdf"

            for repeat, output in ((True, true_path), (False, false_path)):
                doc = document()
                page = doc.page("A4")
                frame = Frame().padding(36)
                frame.add(
                    Table(rows)
                    .column_widths(["45%", "30%", "25%"])
                    .align(["left", "right", "right"])
                    .cell_padding(vertical=7, horizontal=9)
                    .header(background="#0f172a", color="#ffffff", repeat=repeat)
                    .zebra("#f8fafc")
                    .font_size(10)
                    .line_height(13)
                    .stroke("#cbd5e1", 1)
                )
                page.add(frame)
                doc.save(str(output))

            true_counts = [(page.extract_text() or "").count("Revenue") for page in PdfReader(str(true_path)).pages]
            false_counts = [(page.extract_text() or "").count("Revenue") for page in PdfReader(str(false_path)).pages]

            self.assertGreater(len(true_counts), 1)
            self.assertGreater(len(false_counts), 1)
            self.assertEqual(sum(count > 0 for count in true_counts), len(true_counts))
            self.assertEqual(sum(count > 0 for count in false_counts), 1)

    def test_table_after_intro_text_uses_first_page_remaining_space(self) -> None:
        assert PdfReader is not None
        rows = [["Region", "Revenue", "Growth", "Notes"]] + [
            [f"Region {index}", f"${index * 100}K", f"+{(index % 8) + 3}%", "Repeated note text for pagination"]
            for index in range(1, 40)
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "intro_then_table.pdf"
            doc = document()
            page = doc.page("A4")
            frame = Frame().padding(32)
            frame.add_text("Quarterly report").font_size(20).margin(bottom=16)
            frame.add_text("Intro line one for the report.").font_size(12).margin(bottom=8)
            frame.add_text("Intro line two for the report.").font_size(12).margin(bottom=20)
            frame.add(
                Table(rows)
                .column_widths([90, 80, 60, "auto"])
                .align(["left", "right", "right", "left"])
                .cell_padding(vertical=8, horizontal=10)
                .header(background="#1d4ed8", color="#ffffff", repeat=True)
                .font_size(10)
                .line_height(13)
                .background("#ffffff")
                .stroke("#cbd5e1", 1)
            )
            page.add(frame)
            doc.save(str(output))

            page_texts = [(pdf_page.extract_text() or "") for pdf_page in PdfReader(str(output)).pages]
            self.assertGreater(len(page_texts), 1)
            self.assertIn("Region", page_texts[0])


if __name__ == "__main__":
    unittest.main()
