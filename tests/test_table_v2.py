"""Regression tests for Table v2."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from typing import cast

from smart_report import DEFAULT_FONT_NAME, Frame, Spacer, Table, document, get_default_font_name, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts, string_width
from smart_report.builder import resolve_page_size
from smart_report.layout.node import Rect, RenderItem, Style
from smart_report.layout.paginate import _split_flow_child, _split_table_node, _split_text_node, split_frame_node
from smart_report.layout.pass3_heights import resolve_heights
from smart_report.layout.table_model import table_cell_boxes, table_cell_padding, table_column_widths, table_height, table_row_heights
from smart_report.layout.text_wrap import wrap_text
from smart_report.render.painters import paint_table
from smart_report.render.rl_adapter import ReportLabCanvasAdapter

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


class TableV2ModelTests(unittest.TestCase):
    def test_font_fallback_splits_mixed_text_runs(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestSourceHanSansSC", font_dir / "SourceHanSansSC-Normal.ttf")
        original_fallbacks = list(get_fallback_fonts())
        set_fallback_fonts(["TestSourceHanSansSC"])
        try:
            runs = resolve_text_runs("A中B", "Helvetica")
            self.assertEqual([(run.text, run.font_name) for run in runs], [("A", "Helvetica"), ("中", "TestSourceHanSansSC"), ("B", "Helvetica")])
        finally:
            _ = set_fallback_fonts(original_fallbacks)

    def test_font_api_sets_default_for_future_styles(self) -> None:
        original = get_font().name
        try:
            self.assertEqual(set_default_font("Helvetica").name, "Helvetica")
            self.assertEqual(Style().font_name, "Helvetica")
        finally:
            _ = set_default_font(original)

    def test_cjk_wrap_uses_character_boundaries_without_spaces(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(len(text))

        self.assertEqual(wrap_text("中文没有空格", 3, "Helvetica", 12, fixed_width), ["中文没", "有空格"])
        self.assertEqual(wrap_text("superlong", 4, "Helvetica", 12, fixed_width), ["supe", "rlon", "g"])

    def test_cjk_wrap_avoids_bad_line_starts(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(len(text))

        self.assertEqual(wrap_text("你好，世界", 3, "Helvetica", 12, fixed_width), ["你好，", "世界"])

    def test_text_pagination_uses_cjk_wrap_helper(self) -> None:
        text = Frame().add_text("中文没有空格也应该稳定分页")
        text.width(48).font_size(12).line_height(12)
        text.node.resolved_width = 48
        text.node.resolved_height = 60

        slices = _split_text_node(text.node, 24, 24)
        self.assertGreater(len(slices), 1)
        self.assertTrue(all(" " not in str(node.content["text"]) for node in slices))

    def test_rounded_table_painter_clips_cells_and_strokes_outer_radius(self) -> None:
        table = Table([["H1", "H2"], ["A", "B"]]).radius(12).stroke("#94a3b8", 1).background("#ffffff")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        item = RenderItem(table.node, Rect(10, 20, 200, table.node.resolved_height), (), (0,))
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), item)

        self.assertEqual(adapter.rounded_clips, [(10, 20, 200, table.node.resolved_height, 12)])
        self.assertIn(12, adapter.drawn_radii)

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

    def test_colspan_cell_uses_combined_width_and_skips_covered_cells(self) -> None:
        table = Table([["H1", "H2", "H3"], ["Merged", "", "Tail"]]).column_widths([80, 90, 100]).span(1, 0, colspan=2)
        table.node.resolved_width = 270

        boxes = table_cell_boxes(table.node, 0, 0, 270, table_height(table.node))
        body_boxes = [box for box in boxes if box.row_index == 1]
        merged_box = next(box for box in body_boxes if box.column_index == 0)

        self.assertEqual(len(body_boxes), 2)
        self.assertEqual(merged_box.colspan, 2)
        self.assertEqual(merged_box.width, 170)

    def test_rowspan_cell_uses_combined_height_and_skips_covered_cells(self) -> None:
        rows = [["H1", "H2"], ["Group", "A"], ["", "B"]]
        table = Table(rows).column_widths([120, 120]).span(1, 0, rowspan=2)
        table.node.resolved_width = 240
        row_heights = table_row_heights(table.node, rows, table_column_widths(table.node, 240, 2))

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        rowspan_box = next(box for box in boxes if box.row_index == 1 and box.column_index == 0)

        self.assertEqual(len([box for box in boxes if box.row_index in {1, 2}]), 3)
        self.assertEqual(rowspan_box.rowspan, 2)
        self.assertEqual(rowspan_box.height, sum(row_heights[1:3]))

    def test_invalid_span_raises_for_overlap_or_bounds(self) -> None:
        overlapping = Table([["A", "B"], ["C", "D"]]).span(0, 0, rowspan=2).span(1, 0, colspan=2)
        overlapping.node.resolved_width = 200
        with self.assertRaises(ValueError):
            _ = table_height(overlapping.node)

        out_of_bounds = Table([["A", "B"]]).span(0, 1, colspan=2)
        out_of_bounds.node.resolved_width = 200
        with self.assertRaises(ValueError):
            _ = table_height(out_of_bounds.node)

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
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).align("justify")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).align(["left", "justify"])
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).header_style(align="justify")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).header_style(align=["center", "justify"])

    def test_public_font_exports_are_available(self) -> None:
        self.assertEqual(DEFAULT_FONT_NAME, "Helvetica")
        self.assertEqual(get_default_font_name(), get_font().name)
        self.assertGreater(string_width("A", "Helvetica", 12), 0)

    def test_page_size_tuple_validation(self) -> None:
        self.assertEqual(resolve_page_size((200, 300)), (200, 300))
        with self.assertRaises(ValueError):
            _ = resolve_page_size((0, 300))
        with self.assertRaises(ValueError):
            _ = resolve_page_size((float("inf"), 300))

    def test_spacer_requires_fixed_height(self) -> None:
        self.assertEqual(Spacer(12).node.content["height"], 12)
        with self.assertRaises(ValueError):
            _ = Spacer("auto")
        with self.assertRaises(ValueError):
            _ = Spacer(float("inf"))
        with self.assertRaises(ValueError):
            _ = Spacer(float("nan"))
        with self.assertRaises(ValueError):
            _ = Spacer(-1)

    def test_document_save_does_not_accumulate_overlay_padding(self) -> None:
        doc = document()
        doc.header().height(40).add_text("Header")
        page = doc.page("A4")
        page.padding(top=12)
        page.add(Frame().padding(10).add_text("Hello"))
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "stable.pdf"
            doc.save(str(output))
            first_padding = page.node.style.padding.top
            doc.save(str(output))
            second_padding = page.node.style.padding.top
            page.padding(top=60)
            doc.save(str(output))
            updated_padding = page.node.style.padding.top
        self.assertEqual(first_padding, 40)
        self.assertEqual(second_padding, 40)
        self.assertEqual(updated_padding, 60)


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

    def test_table_pagination_keeps_rowspan_rows_together(self) -> None:
        rows = [["Region", "Value"], ["A", "1"], ["Merged", "2"], ["", "3"], ["D", "4"]]
        table = Table(rows).column_widths([120, 120]).span(2, 0, rowspan=2).font_size(10).line_height(12)
        table.node.resolved_width = 240
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 72, 72)
        source_sets = [set(cast(list[int], table_slice.content["source_row_indices"])) for table_slice in slices]
        slice_with_span = next(table_slice for table_slice in slices if {2, 3}.issubset(set(cast(list[int], table_slice.content["source_row_indices"]))))
        slice_spans = cast(dict[str, dict[str, int]], slice_with_span.content["cell_spans"])

        self.assertTrue(any({2, 3}.issubset(source_set) for source_set in source_sets))
        self.assertTrue(all(not ({2, 3}.intersection(source_set) and not {2, 3}.issubset(source_set)) for source_set in source_sets))
        self.assertIn({"rowspan": 2, "colspan": 1}, slice_spans.values())

    def test_nested_frame_splits_across_pages(self) -> None:
        outer = Frame().padding(4)
        nested = outer.add_frame().padding(2)
        for index in range(8):
            nested.add_text(f"Nested line {index}").font_size(10).line_height(12)
        outer.node.resolved_width = 200
        nested.node.resolved_width = 180
        for child in nested.node.children:
            child.resolved_width = 180
            child.resolved_height = 12
        nested.node.resolved_height = 8 * 12 + 4

        slices = split_frame_node(outer.node, 44, 44)

        self.assertGreater(len(slices), 1)
        self.assertTrue(all(slice_node.children for slice_node in slices))
        self.assertTrue(all(slice_node.resolved_height <= 44 for slice_node in slices))

    def test_fixed_height_rect_splits_by_available_height(self) -> None:
        rect = Frame().add_rect().height(120).background("#dbeafe")
        rect.node.resolved_width = 100
        rect.node.resolved_height = 120

        slices = _split_flow_child(rect.node, 50, 40)
        shell = Frame()
        shell.node.resolved_width = 100
        for slice_node in slices:
            _ = shell.node.add_child(slice_node)
        resolve_heights(shell.node, None)

        self.assertEqual([slice_node.resolved_height for slice_node in slices], [50, 40, 30])

    def test_fixed_height_split_rejects_non_finite_height(self) -> None:
        rect = Frame().add_rect().height(120)
        rect.node.resolved_width = 100
        rect.node.resolved_height = float("inf")

        with self.assertRaises(ValueError):
            _ = _split_flow_child(rect.node, 50, 40)


class LayoutPrimitiveTests(unittest.TestCase):
    def test_layout_api_rejects_unbounded_track_counts_and_nonfinite_gap(self) -> None:
        with self.assertRaises(ValueError):
            _ = Frame().columns(65)
        with self.assertRaises(ValueError):
            _ = Frame().grid(65)
        with self.assertRaises(ValueError):
            _ = Frame().gap(float("inf"))
        with self.assertRaises(ValueError):
            _ = Frame().flex("row", wrap=True)

    def test_flex_row_positions_children_horizontally(self) -> None:
        frame = Frame().flex("row", gap=10).width(300)
        first = frame.add_text("A")
        second = frame.add_text("B")
        frame.node.resolved_width = 300
        for child in frame.node.children:
            child.resolved_width = 145
            child.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container

        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_x, 0)
        self.assertEqual(second.node.local_x, 155)
        self.assertEqual(frame.node.resolved_height, 20)

    def test_grid_positions_children_in_tracks(self) -> None:
        frame = Frame().grid(2, gap=8).width(208)
        children = [frame.add_text(str(index)) for index in range(3)]
        frame.node.resolved_width = 208
        for child in frame.node.children:
            child.resolved_width = 100
            child.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container

        _layout_container(frame.node, None)

        self.assertEqual((children[0].node.local_x, children[0].node.local_y), (0, 0))
        self.assertEqual((children[1].node.local_x, children[1].node.local_y), (108, 0))
        self.assertEqual((children[2].node.local_x, children[2].node.local_y), (0, 28))

    def test_columns_place_children_in_shortest_column(self) -> None:
        frame = Frame().columns(2, gap=12).width(212)
        children = [frame.add_text(str(index)) for index in range(3)]
        frame.node.resolved_width = 212
        heights = [40, 20, 20]
        for child, height in zip(frame.node.children, heights):
            child.resolved_width = 100
            child.resolved_height = height

        from smart_report.layout.pass3_heights import _layout_container

        _layout_container(frame.node, None)

        self.assertEqual(children[0].node.local_x, 0)
        self.assertEqual(children[1].node.local_x, 112)
        self.assertEqual(children[2].node.local_x, 112)
        self.assertEqual(children[2].node.local_y, 32)


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

class _SpyAdapter:
    def __init__(self) -> None:
        self.rounded_clips: list[tuple[float, float, float, float, float]] = []
        self.drawn_radii: list[float] = []

    @contextmanager
    def isolated_state(self) -> Iterator["_SpyAdapter"]:
        yield self

    def apply_clip_rounded_rect(self, rect: Rect, radius: float) -> None:
        self.rounded_clips.append((rect.x, rect.y, rect.width, rect.height, radius))

    def apply_clip_rect(self, _rect: Rect) -> None:
        return

    def draw_rect(self, rect: Rect, fill: object = None, stroke: object = None, stroke_width: float = 0.0, radius: float = 0.0) -> None:
        _ = (rect, fill, stroke, stroke_width)
        self.drawn_radii.append(radius)

    def draw_text(self, **_kwargs: object) -> None:
        return


if __name__ == "__main__":
    unittest.main()
