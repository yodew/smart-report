"""Regression tests for Table v2."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Iterator
from typing import cast

from smart_report import DEFAULT_FONT_NAME, Frame, Image, Spacer, Table, Text, document, get_default_font_name, get_fallback_fonts, get_font, register_font, resolve_text_runs, set_default_font, set_fallback_fonts, string_width
from smart_report.builder import resolve_page_size
from smart_report.layout.node import LayoutNode, Rect, RenderItem, Style
from smart_report.layout.paginate import _split_flow_child, _split_table_node, _split_text_node, paginate_page, split_frame_node
from smart_report.layout.pass4_render import build_render_list
from smart_report.layout.pass3_heights import resolve_heights
from smart_report.layout.table_model import table_cell_boxes, table_cell_padding, table_column_widths, table_height, table_row_heights, table_rows
from smart_report.layout.text_wrap import wrap_text
from smart_report.render.painters import paint_image, paint_render_item, paint_table
from smart_report.render.rl_adapter import DEFAULT_TEXT_COLOR, ReportLabCanvasAdapter
from smart_report.style.typography import shape_text

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

    def test_typography_auto_shapes_arabic_text_for_measurement(self) -> None:
        shaped = shape_text("مرحبا", "auto", "rtl")

        self.assertNotEqual(shaped, "مرحبا")
        self.assertTrue(any("\ufe70" <= character <= "\ufeff" for character in shaped))

    def test_text_wrap_uses_typography_width_for_auto_mode(self) -> None:
        measured: list[str] = []

        def shaped_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            measured.append(text)
            return float(len(text))

        _ = wrap_text("مرحبا", 3, "Helvetica", 12, shaped_width, "auto", "rtl")

        self.assertTrue(any(candidate != "مرحبا" for candidate in measured))

    def test_text_builder_stores_typography_options(self) -> None:
        text = Text("مرحبا").typography("auto").text_direction("rtl")

        self.assertEqual(text.node.style.typography, "auto")
        self.assertEqual(text.node.style.text_direction, "rtl")

    def test_table_cell_boxes_carry_typography_options(self) -> None:
        table = Table([["Label", "مرحبا"]]).typography("auto").text_direction("rtl")
        table.node.resolved_width = 200

        boxes = table_cell_boxes(table.node, 0, 0, 200, table_height(table.node))

        self.assertTrue(all(box.typography == "auto" for box in boxes))
        self.assertTrue(all(box.text_direction == "rtl" for box in boxes))

    def test_adapter_draw_text_emits_shaped_text_for_auto_typography(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestNotoNaskhArabic-Medium", font_dir / "NotoNaskhArabic-Medium.ttf")
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        adapter._canvas = _FakeCanvas()
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.draw_text(
            x=10,
            y=10,
            width=160,
            text="مرحبا",
            font_name="TestNotoNaskhArabic-Medium",
            font_size=12,
            line_height=14,
            color=None,
            typography="auto",
            text_direction="rtl",
        )

        output = "".join(adapter._canvas.text_object.output)
        self.assertNotEqual(output, "مرحبا")
        self.assertTrue(any("\ufe70" <= character <= "\ufeff" for character in output))
        self.assertIn("TestNotoNaskhArabic-Medium", adapter._canvas.text_object.font_names)
        self.assertNotIn("Helvetica", adapter._canvas.text_object.font_names)

    def test_arabic_font_supports_shaped_presentation_forms(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestNotoNaskhArabic-Support", font_dir / "NotoNaskhArabic-Medium.ttf")

        shaped = shape_text("مرحبا", "auto", "rtl")
        runs = resolve_text_runs(shaped, "TestNotoNaskhArabic-Support")

        self.assertEqual({run.font_name for run in runs}, {"TestNotoNaskhArabic-Support"})

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

    def test_frame_background_is_painted_by_render_pipeline(self) -> None:
        frame = Frame().background("#f8fafc").size(120, 40)
        frame.node.resolved_width = 120
        frame.node.resolved_height = 40
        adapter = _SpyAdapter()

        for item in build_render_list(frame.node):
            paint_render_item(cast(ReportLabCanvasAdapter, adapter), item)

        self.assertIn(frame.node.style.background, adapter.rect_fills)

    def test_rich_table_cell_uses_nested_layout_content(self) -> None:
        rich_cell = Frame().padding(4)
        rich_cell.add_text("Nested table content wraps inside a cell").font_size(10).line_height(12)
        table = Table([["Name", "Details"], ["A", rich_cell]]).column_widths([80, 120]).cell_padding(4)
        table.node.resolved_width = 200

        height = table_height(table.node)
        boxes = table_cell_boxes(table.node, 0, 0, 200, height)
        rich_box = next(box for box in boxes if box.row_index == 1 and box.column_index == 1)

        self.assertIsNotNone(rich_box.rich_content)
        self.assertGreater(rich_box.height, 24)

    def test_rich_table_cell_frame_background_is_painted(self) -> None:
        rich_cell = Frame().padding(4).background("#f8fafc")
        rich_cell.add_text("Nested table content").font_size(10).line_height(12)
        table = Table([["Name", "Details"], ["A", rich_cell]]).column_widths([80, 120]).cell_padding(4)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        self.assertIn(rich_cell.node.style.background, adapter.rect_fills)

    def test_table_footer_repeats_in_paginated_slices(self) -> None:
        rows = [["Metric", "Value"]] + [[f"M{index}", str(index)] for index in range(12)]
        table = Table(rows).footer([["Total", "66"]], repeat=True, background="#e2e8f0")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 90, 90)

        self.assertGreater(len(slices), 1)
        self.assertTrue(all(table_rows(table_slice)[-1][0] == "Total" for table_slice in slices))

    def test_non_repeated_footer_keeps_footer_style_on_final_slice(self) -> None:
        rows = [["Metric", "Value"]] + [[f"M{index}", str(index)] for index in range(12)]
        table = Table(rows).footer([["Total", "66"]], repeat=False, background="#e2e8f0")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 90, 90)
        final_slice = slices[-1]
        boxes = table_cell_boxes(final_slice, 0, 0, 200, final_slice.resolved_height)
        footer_box = next(box for box in boxes if box.row_index == len(table_rows(final_slice)) - 1 and box.column_index == 0)

        self.assertGreater(len(slices), 1)
        self.assertTrue(all(table_rows(table_slice)[-1][0] != "Total" for table_slice in slices[:-1]))
        self.assertEqual(table_rows(final_slice)[-1][0], "Total")
        self.assertEqual(footer_box.background, table.node.content["footer_background"])

    def test_footer_background_takes_precedence_over_zebra(self) -> None:
        table = (
            Table([["Metric", "Value"], ["A", "1"], ["B", "2"]])
            .zebra("#111111")
            .footer([["Total", "3"]], background="#e2e8f0")
        )
        table.node.resolved_width = 200
        boxes = table_cell_boxes(table.node, 0, 0, 200, table_height(table.node))
        footer_box = next(box for box in boxes if box.row_index == 3 and box.column_index == 0)

        self.assertEqual(footer_box.background, table.node.content["footer_background"])

    def test_cell_border_override_is_reflected_in_cell_box(self) -> None:
        table = Table([["A", "B"]]).borders("#111827", width=0.5, inner_width=0.25, outer_width=2).cell_border(0, 1, color="#dc2626", width=3)
        table.node.resolved_width = 200
        boxes = table_cell_boxes(table.node, 0, 0, 200, table_height(table.node))
        cell = next(box for box in boxes if box.column_index == 1)

        self.assertEqual(cell.border_width, 3)

    def test_cell_border_override_controls_painted_line_widths(self) -> None:
        table = Table([["A", "B"]]).borders("#111827", width=0.5, inner_width=0.25, outer_width=2).cell_border(0, 1, color="#dc2626", width=3)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        self.assertIn(3, adapter.line_widths)

    def test_table_inner_and_outer_border_widths_are_painted(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=0.5, inner_width=0.25, outer_width=2)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        self.assertIn(0.25, adapter.line_widths)
        self.assertIn(2, adapter.line_widths)

    def test_cell_border_override_is_painted_after_neighbor_borders(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=0.5, inner_width=0.25, outer_width=2).cell_border(0, 0, width=3)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        self.assertEqual(adapter.line_widths[-4:], [3, 3, 3, 3])

    def test_table_cell_backgrounds_do_not_bleed_between_cells(self) -> None:
        table = Table([["A", "B"]]).cell_style(0, 0, background="#dcfce7")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        cell_styles = cast(dict[str, dict[str, object]], table.node.content["cell_styles"])
        self.assertEqual(adapter.rect_fills.count(cell_styles["0:0"]["background"]), 1)
        self.assertGreaterEqual(adapter.rect_fills.count(None), 1)

    def test_draw_text_defaults_to_black_when_color_is_none(self) -> None:
        fake_canvas = _FakeCanvas()
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_text(10, 10, 100, "Hello", "Helvetica", 12, 14, None)

        self.assertEqual(fake_canvas.text_object.fill_colors[0], (DEFAULT_TEXT_COLOR.red, DEFAULT_TEXT_COLOR.green, DEFAULT_TEXT_COLOR.blue))
        self.assertEqual(fake_canvas.fill_alphas[0], DEFAULT_TEXT_COLOR.alpha)

    def test_pagination_control_flags_affect_frame_splitting(self) -> None:
        frame = Frame().padding(0)
        first = Spacer(20)
        second = Spacer(20).page_break_before()
        frame.add(first).add(second)
        frame.node.resolved_width = 200
        frame.node.resolved_height = 40
        for child in frame.node.children:
            child.resolved_width = 200
            child.resolved_height = 20

        slices = split_frame_node(frame.node, 100, 100)

        self.assertEqual(len(slices), 2)
        self.assertEqual(len(slices[0].children), 1)
        self.assertEqual(len(slices[1].children), 1)

    def test_keep_together_prevents_fixed_height_split_when_following_page_can_fit(self) -> None:
        spacer = Spacer(80).keep_together()
        spacer.node.resolved_height = 80

        slices = _split_flow_child(spacer.node, 40, 100)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].resolved_height, 80)

    def test_image_bytes_fit_and_rounded_clip_are_supported(self) -> None:
        image_bytes = _png_bytes(16, 8)
        image = Image(image_bytes).contain().radius(5).width(80)
        image.node.resolved_width = 80
        image.node.resolved_height = 40
        adapter = _SpyAdapter()

        paint_image(cast(ReportLabCanvasAdapter, adapter), RenderItem(image.node, Rect(10, 20, 80, 40), (), (0,)))

        self.assertEqual(adapter.rounded_clips, [(10, 20, 80, 40, 5)])
        self.assertEqual(adapter.images[0][1], "contain")


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

    def test_rich_table_cell_splits_across_table_slices(self) -> None:
        rich_cell = Frame().padding(0)
        for _ in range(5):
            rich_cell.add(Spacer(20))
        table = (
            Table([["Metric", "Details"], ["Revenue", rich_cell]])
            .column_widths([100, 160])
            .header(background="#1d4ed8", color="#ffffff", repeat=True)
            .footer([["Total", "216K"]], repeat=True, background="#e2e8f0")
            .cell_style(1, 1, background="#dcfce7")
            .cell_padding(vertical=6, horizontal=6)
        )
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 90, 90)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]
        detail_cells = []
        for table_slice in slices:
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            if 1 in slice_source_rows:
                detail_cells.append(cast(list[list[object]], table_slice.content["rows"])[slice_source_rows.index(1)][1])
        styled_fragment_boxes = []
        for table_slice in slices:
            slice_rows = cast(list[list[object]], table_slice.content["rows"])
            self.assertEqual(slice_rows[0], ["Metric", "Details"])
            self.assertEqual(slice_rows[-1], ["Total", "216K"])
            styled_fragment_boxes.extend(
                box
                for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
                if box.source_row_index == 1 and box.column_index == 1
            )

        self.assertGreater(len(slices), 1)
        self.assertGreater(source_rows.count(1), 1)
        self.assertTrue(all(isinstance(cell, LayoutNode) for cell in detail_cells))
        self.assertTrue(all(table_slice.resolved_height <= 90 for table_slice in slices))
        self.assertEqual(len(styled_fragment_boxes), source_rows.count(1))
        self.assertTrue(all(box.background is not None for box in styled_fragment_boxes))

    def test_unrelated_span_does_not_disable_rich_table_cell_splitting(self) -> None:
        rich_cell = Frame().padding(0)
        for _ in range(5):
            rich_cell.add(Spacer(20))
        table = Table([["Metric", "Details"], ["Merged", ""], ["Revenue", rich_cell]]).column_widths([100, 160]).cell_padding(vertical=6, horizontal=6).span(1, 0, colspan=2)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)
        self.assertGreater(source_rows.count(2), 1)

    def test_rich_table_cell_with_span_remains_atomic(self) -> None:
        rich_cell = Frame().padding(0)
        for _ in range(5):
            rich_cell.add(Spacer(20))
        table = Table([["Metric", "Details"], [rich_cell, ""], ["Tail", "Done"]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6).span(1, 0, colspan=2)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_row_with_multiple_rich_table_cells_remains_atomic(self) -> None:
        first_cell = Frame().padding(0)
        second_cell = Frame().padding(0)
        for _ in range(5):
            first_cell.add(Spacer(20))
            second_cell.add(Spacer(20))
        table = Table([["Left", "Right"], [first_cell, second_cell]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_rich_text_table_cell_splits_across_table_slices(self) -> None:
        rich_text = Text(" ".join(f"note-{index}" for index in range(60))).font_size(10).line_height(12)
        table = Table([["Metric", "Details"], ["Revenue", rich_text]]).column_widths([100, 160]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]
        detail_cells = []
        for table_slice in slices:
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            if 1 in slice_source_rows:
                detail_cells.append(cast(list[list[object]], table_slice.content["rows"])[slice_source_rows.index(1)][1])

        self.assertGreater(source_rows.count(1), 1)
        self.assertTrue(all(isinstance(cell, LayoutNode) and cell.node_type == "text" for cell in detail_cells))
        self.assertTrue(all(table_slice.resolved_height <= 70 for table_slice in slices))

    def test_row_with_multiple_rich_text_cells_splits_across_table_slices(self) -> None:
        first_text = Text(" ".join(f"left-{index}" for index in range(80))).font_size(10).line_height(12)
        second_text = Text(" ".join(f"right-{index}" for index in range(80))).font_size(10).line_height(12)
        table = (
            Table([["Metric", "Left", "Right"], ["Revenue", first_text, second_text]])
            .column_widths([80, 100, 100])
            .header(background="#1d4ed8", color="#ffffff", repeat=True)
            .footer([["Total", "Reviewed", "Tracked"]], repeat=True, background="#e2e8f0")
            .cell_style(1, 1, background="#dcfce7")
            .cell_style(1, 2, background="#e0f2fe")
            .cell_padding(vertical=6, horizontal=6)
        )
        table.node.resolved_width = 280
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 82, 82)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]
        text_cells: list[object] = []
        styled_fragment_boxes = []
        for table_slice in slices:
            slice_rows = cast(list[list[object]], table_slice.content["rows"])
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            self.assertEqual(slice_rows[0], ["Metric", "Left", "Right"])
            self.assertEqual(slice_rows[-1], ["Total", "Reviewed", "Tracked"])
            if 1 in slice_source_rows:
                row = slice_rows[slice_source_rows.index(1)]
                text_cells.extend([row[1], row[2]])
            styled_fragment_boxes.extend(
                box
                for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
                if box.source_row_index == 1 and box.column_index in {1, 2}
            )

        self.assertGreater(source_rows.count(1), 1)
        self.assertTrue(any(isinstance(cell, LayoutNode) and cell.node_type == "text" for cell in text_cells))
        self.assertTrue(all(table_slice.resolved_height <= 82 for table_slice in slices))
        self.assertEqual(len(styled_fragment_boxes), source_rows.count(1) * 2)
        self.assertTrue(all(box.background is not None for box in styled_fragment_boxes))

    def test_rich_text_table_cell_with_span_remains_atomic(self) -> None:
        rich_text = Text(" ".join(f"note-{index}" for index in range(60))).font_size(10).line_height(12)
        table = Table([["Metric", "Details"], [rich_text, ""]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6).span(1, 0, colspan=2)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_row_with_rich_text_and_rich_frame_cells_splits_across_table_slices(self) -> None:
        rich_text = Text(" ".join(f"note-{index}" for index in range(60))).font_size(10).line_height(12)
        rich_frame = Frame().padding(0)
        for _ in range(5):
            rich_frame.add(Spacer(20))
        table = (
            Table([["Left", "Right"], [rich_text, rich_frame]])
            .column_widths([130, 130])
            .cell_style(1, 0, background="#dcfce7")
            .cell_style(1, 1, background="#e0f2fe")
            .cell_padding(vertical=6, horizontal=6)
        )
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]
        rich_cells = []
        styled_fragment_boxes = []
        for table_slice in slices:
            slice_rows = cast(list[list[object]], table_slice.content["rows"])
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            if 1 in slice_source_rows:
                row = slice_rows[slice_source_rows.index(1)]
                rich_cells.extend([row[0], row[1]])
            styled_fragment_boxes.extend(
                box
                for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
                if box.source_row_index == 1 and box.column_index in {0, 1}
            )

        self.assertGreater(source_rows.count(1), 1)
        self.assertTrue(any(isinstance(cell, LayoutNode) and cell.node_type == "text" for cell in rich_cells))
        self.assertTrue(any(isinstance(cell, LayoutNode) and cell.node_type == "frame" for cell in rich_cells))
        self.assertEqual(len(styled_fragment_boxes), source_rows.count(1) * 2)
        self.assertTrue(all(box.background is not None for box in styled_fragment_boxes))

    def test_row_with_multiple_rich_frame_cells_remains_atomic(self) -> None:
        first_frame = Frame().padding(0)
        second_frame = Frame().padding(0)
        for _ in range(5):
            first_frame.add(Spacer(20))
            second_frame.add(Spacer(20))
        table = Table([["Left", "Right"], [first_frame, second_frame]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_row_with_rich_text_and_rich_image_cells_remains_atomic(self) -> None:
        rich_text = Text(" ".join(f"note-{index}" for index in range(60))).font_size(10).line_height(12)
        rich_image = Image(_png_bytes(16, 40)).size(40, 100)
        table = Table([["Left", "Right"], [rich_text, rich_image]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_single_rich_image_table_cell_remains_atomic(self) -> None:
        rich_image = Image(_png_bytes(16, 40)).size(40, 100)
        table = Table([["Metric", "Image"], ["Preview", rich_image]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_multiple_rich_text_table_cells_with_span_remain_atomic(self) -> None:
        first_text = Text(" ".join(f"left-{index}" for index in range(60))).font_size(10).line_height(12)
        second_text = Text(" ".join(f"right-{index}" for index in range(60))).font_size(10).line_height(12)
        table = Table([["Metric", "Left", "Right"], ["Revenue", first_text, second_text]]).column_widths([80, 100, 100]).cell_padding(vertical=6, horizontal=6).span(1, 1, colspan=2)
        table.node.resolved_width = 280
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

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

    def test_image_moves_to_next_frame_slice_when_current_page_lacks_space(self) -> None:
        frame = Frame().padding(0)
        image = Image(_png_bytes(16, 40)).size(40, 80)
        frame.add(image)
        frame.node.resolved_width = 100
        frame.node.resolved_height = 80
        image.node.resolved_width = 40
        image.node.resolved_height = 80

        slices = split_frame_node(frame.node, 40, 100)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].children[0].node_type, "image")
        self.assertEqual(slices[0].children[0].resolved_height, 80)
        self.assertEqual(slices[0].resolved_height, 80)

    def test_svg_image_moves_to_next_frame_slice_when_current_page_lacks_space(self) -> None:
        frame = Frame().padding(0)
        image = Image("examples/box.svg").size(80, 80)
        frame.add(image)
        frame.node.resolved_width = 100
        frame.node.resolved_height = 80
        image.node.resolved_width = 80
        image.node.resolved_height = 80

        slices = split_frame_node(frame.node, 40, 100)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].children[0].node_type, "image")
        self.assertEqual(slices[0].children[0].content["src"], "examples/box.svg")

    def test_image_frame_slice_starts_on_next_paginated_page_when_current_page_lacks_space(self) -> None:
        page = document().page((100, 100))
        intro = page.add_spacer(60)
        frame = Frame().padding(0)
        image = Image(_png_bytes(16, 40)).size(40, 80)
        frame.add(image)
        page.add(frame)
        page.node.resolved_width = 100
        page.node.resolved_height = 100
        intro.node.resolved_width = 100
        intro.node.resolved_height = 60
        intro.node.local_y = 0
        frame.node.resolved_width = 100
        frame.node.resolved_height = 80
        frame.node.local_y = 60
        image.node.resolved_width = 40
        image.node.resolved_height = 80

        pages = paginate_page(page.node)

        self.assertEqual(len(pages), 2)
        self.assertEqual([child.node_type for child in pages[0].children], ["spacer"])
        self.assertEqual([child.node_type for child in pages[1].children], ["frame"])
        self.assertEqual(pages[1].children[0].children[0].node_type, "image")

    def test_oversized_image_remains_atomic_when_following_page_cannot_fit_it(self) -> None:
        frame = Frame().padding(0)
        image = Image(_png_bytes(16, 40)).size(40, 140)
        frame.add(image)
        frame.node.resolved_width = 100
        frame.node.resolved_height = 140
        image.node.resolved_width = 40
        image.node.resolved_height = 140

        slices = split_frame_node(frame.node, 40, 100)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].children[0].node_type, "image")
        self.assertEqual(slices[0].children[0].resolved_height, 140)

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

    def test_flex_column_gap_positions_children_vertically(self) -> None:
        frame = Frame().flex("column", gap=10).width(120)
        first = Spacer(20)
        second = Spacer(30)
        frame.add(first).add(second)
        frame.node.resolved_width = 120
        first.node.resolved_width = 120
        first.node.resolved_height = 20
        second.node.resolved_width = 120
        second.node.resolved_height = 30

        resolve_heights(frame.node, None)

        self.assertEqual((first.node.local_x, first.node.local_y), (0, 0))
        self.assertEqual((second.node.local_x, second.node.local_y), (0, 30))
        self.assertEqual(frame.node.resolved_height, 60)

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

    def test_auto_height_resolves_percentage_absolute_top_against_final_content_height(self) -> None:
        frame = Frame().width(100)
        marker = Spacer(20).absolute(0, "50%")
        frame.add(marker)
        frame.node.resolved_width = 100
        marker.node.resolved_width = 100
        marker.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual(marker.node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 40)

    def test_auto_height_percentage_absolute_top_includes_flow_content(self) -> None:
        frame = Frame().width(100).padding(vertical=10)
        flow = frame.add_spacer(80)
        marker = Spacer(20).absolute(0, "50%")
        frame.add(marker)
        frame.node.resolved_width = 100
        flow.node.resolved_width = 100
        flow.node.resolved_height = 80
        marker.node.resolved_width = 100
        marker.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual(marker.node.local_y, 50)
        self.assertEqual(frame.node.resolved_height, 100)

    def test_auto_height_rejects_percentage_absolute_top_at_or_above_full_height(self) -> None:
        frame = Frame().width(100)
        marker = Spacer(20).absolute(0, "100%")
        frame.add(marker)
        frame.node.resolved_width = 100
        marker.node.resolved_width = 100
        marker.node.resolved_height = 20

        with self.assertRaises(ValueError):
            resolve_heights(frame.node, None)

    def test_auto_height_rejects_percentage_absolute_top_even_for_zero_height_child(self) -> None:
        frame = Frame().width(100)
        marker = Spacer(0).absolute(0, "150%")
        frame.add(marker)
        frame.node.resolved_width = 100
        marker.node.resolved_width = 100
        marker.node.resolved_height = 0

        with self.assertRaises(ValueError):
            resolve_heights(frame.node, None)

    def test_flex_auto_height_includes_absolute_percentage_child_extent(self) -> None:
        frame = Frame().flex("row", gap=10).width(220)
        first = frame.add_text("A")
        second = frame.add_text("B")
        marker = Spacer(30).absolute(0, "75%")
        frame.add(marker)
        frame.node.resolved_width = 220
        for child in (first.node, second.node):
            child.resolved_width = 100
            child.resolved_height = 20
        marker.node.resolved_width = 100
        marker.node.resolved_height = 30

        resolve_heights(frame.node, None)

        self.assertEqual((first.node.local_x, second.node.local_x), (0, 110))
        self.assertEqual(marker.node.local_y, 90)
        self.assertEqual(frame.node.resolved_height, 120)

    def test_grid_auto_height_includes_absolute_percentage_child_extent(self) -> None:
        frame = Frame().grid(2, gap=8).width(208)
        children = [frame.add_text(str(index)) for index in range(2)]
        marker = Spacer(20).absolute(0, "50%")
        frame.add(marker)
        frame.node.resolved_width = 208
        for child in children:
            child.node.resolved_width = 100
            child.node.resolved_height = 20
        marker.node.resolved_width = 100
        marker.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((children[0].node.local_x, children[1].node.local_x), (0, 108))
        self.assertEqual(marker.node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 40)

    def test_columns_auto_height_includes_absolute_percentage_child_extent(self) -> None:
        frame = Frame().columns(2, gap=12).width(212)
        first = frame.add_text("A")
        second = frame.add_text("B")
        marker = Spacer(20).absolute(0, "50%")
        frame.add(marker)
        frame.node.resolved_width = 212
        first.node.resolved_width = 100
        first.node.resolved_height = 40
        second.node.resolved_width = 100
        second.node.resolved_height = 20
        marker.node.resolved_width = 100
        marker.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((first.node.local_x, second.node.local_x), (0, 112))
        self.assertEqual(marker.node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 40)


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
        self.rect_fills: list[object] = []
        self.images: list[tuple[Rect, str]] = []
        self.line_widths: list[float] = []
        self.lines: list[tuple[float, float, float, float, float]] = []

    @contextmanager
    def isolated_state(self) -> Iterator["_SpyAdapter"]:
        yield self

    def apply_clip_rounded_rect(self, rect: Rect, radius: float) -> None:
        self.rounded_clips.append((rect.x, rect.y, rect.width, rect.height, radius))

    def apply_clip_rect(self, _rect: Rect) -> None:
        return

    def draw_rect(self, rect: Rect, fill: object = None, stroke: object = None, stroke_width: float = 0.0, radius: float = 0.0) -> None:
        _ = (rect, fill, stroke, stroke_width)
        self.rect_fills.append(fill)
        self.drawn_radii.append(radius)

    def draw_text(self, **_kwargs: object) -> None:
        return

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, _color: object, stroke_width: float) -> None:
        self.line_widths.append(float(stroke_width))
        self.lines.append((float(x1), float(y1), float(x2), float(y2), float(stroke_width)))

    def draw_image(self, _source: object, rect: Rect, opacity: float = 1.0, fit: str = "stretch") -> None:
        _ = opacity
        self.images.append((rect, fit))


def _png_bytes(width: int, height: int) -> bytes:
    from PIL import Image as PillowImage

    buffer = BytesIO()
    image = PillowImage.new("RGB", (width, height), "white")
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeTextObject:
    def __init__(self) -> None:
        self.fill_colors: list[tuple[float, float, float]] = []
        self.origins: list[tuple[float, float]] = []
        self.output: list[str] = []
        self.font_names: list[str] = []

    def setFont(self, _font_name: str, _font_size: float, _leading: float | None = None) -> None:
        _ = (_font_size, _leading)
        self.font_names.append(_font_name)

    def setFillColorRGB(self, red: float, green: float, blue: float) -> None:
        self.fill_colors.append((red, green, blue))

    def setTextOrigin(self, _x: float, _y: float) -> None:
        self.origins.append((_x, _y))

    def setLeading(self, _leading: float) -> None:
        return

    def textOut(self, _text: str) -> None:
        self.output.append(_text)

    def textLine(self, _text: str = "") -> None:
        return


class _FakeCanvas:
    def __init__(self) -> None:
        self.text_object = _FakeTextObject()
        self.fill_alphas: list[float] = []

    def beginText(self, x: float, y: float) -> _FakeTextObject:
        _ = (x, y)
        return self.text_object

    def drawText(self, text_object: object) -> None:
        _ = text_object
        return

    def saveState(self) -> None:
        return

    def restoreState(self) -> None:
        return

    def setFillColorRGB(self, r: float, g: float, b: float) -> None:
        _ = (r, g, b)
        return

    def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:
        _ = (r, g, b)
        return

    def setFillAlpha(self, alpha: float) -> None:
        self.fill_alphas.append(alpha)

    def setStrokeAlpha(self, alpha: float) -> None:
        _ = alpha
        return

    def setLineWidth(self, width: float) -> None:
        _ = width
        return

    def rect(self, x: float, y: float, width: float, height: float, stroke: int = 1, fill: int = 0) -> None:
        _ = (x, y, width, height, stroke, fill)

    def roundRect(self, x: float, y: float, width: float, height: float, radius: float, stroke: int = 1, fill: int = 0) -> None:
        _ = (x, y, width, height, radius, stroke, fill)

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        _ = (x1, y1, x2, y2)
        return

    def beginPath(self) -> object:
        return object()

    def clipPath(self, path: object, stroke: int = 0, fill: int = 0) -> None:
        _ = (path, stroke, fill)

    def setFont(self, font_name: str, font_size: float, leading: float | None = None) -> None:
        _ = (font_name, font_size, leading)
        return

    def drawImage(self, image: object, x: float, y: float, width: float, height: float, mask: object | None = None) -> None:
        _ = (image, x, y, width, height, mask)

    def translate(self, dx: float, dy: float) -> None:
        _ = (dx, dy)
        return

    def scale(self, x: float, y: float) -> None:
        _ = (x, y)
        return

    def setPageSize(self, size: tuple[float, float]) -> None:
        _ = size
        return

    def showPage(self) -> None:
        return

    def save(self) -> None:
        return


if __name__ == "__main__":
    unittest.main()
