"""Regression tests for Table v2."""

from __future__ import annotations

import importlib
import tempfile
import unittest
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import Sequence
from typing import cast

from smart_report import DEFAULT_FONT_NAME, Frame, Image, RichText, Spacer, Table, Text, document, get_default_font_name, get_fallback_font_families, get_fallback_fonts, get_font, get_font_family, register_font, register_font_family, resolve_text_runs, set_default_font, set_fallback_font_families, set_fallback_fonts, shaped_string_width, string_width
from smart_report.builder import resolve_page_size
from smart_report.layout.node import CornerRadii, Edges, LayoutNode, Rect, RenderItem, Style, clone_layout_node
from smart_report.layout.paginate import STARTS_ON_FOLLOWING_PAGE, _split_flow_child, _split_table_node, _split_text_node, paginate_page, split_frame_node
from smart_report.layout.pass4_render import build_render_list
from smart_report.layout.pass3_heights import resolve_heights
from smart_report.layout.pass2_widths import resolve_widths
from smart_report.layout.rich_text_layout import layout_rich_text, rich_text_runs_for_lines
from smart_report.layout.table_model import TableCellBox, fit_plain_overflow_text, plain_cell_natural_width, plain_overflow_text_width, table_cell_box_natural_width, table_cell_boxes, table_cell_padding, table_column_widths, table_height, table_row_heights, table_rows
from smart_report.layout.text_wrap import wrap_text
from smart_report.render.painters import paint_image, paint_render_item, paint_rich_text, paint_table, paint_text
from smart_report.render.rl_adapter import DEFAULT_TEXT_COLOR, ReportLabCanvasAdapter
from smart_report.style.color import parse_color
from smart_report.style.typography import shape_text
import smart_report.layout.table_model as table_model_module
import smart_report.style.font as font_module

RectBuilder = cast(Any, importlib.import_module("smart_report.elements.shape").Rect)

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def _page_link_annotation_uris(reader: Any) -> list[list[str]]:
    pages: list[list[str]] = []
    for page in reader.pages:
        page_uris: list[str] = []
        annotations = page.get("/Annots") or []
        for annotation in annotations:
            annotation_object = annotation.get_object()
            if annotation_object.get("/Subtype") != "/Link":
                continue
            action = annotation_object.get("/A")
            if action is None:
                continue
            uri = action.get("/URI")
            if isinstance(uri, str):
                page_uris.append(uri)
        pages.append(page_uris)
    return pages


class TableV2ModelTests(unittest.TestCase):

    def test_base14_fonts_are_available_without_registration(self) -> None:
        self.assertGreater(string_width("Header", "Helvetica-Bold", 12), 0)
        self.assertGreater(string_width("Body", "Times-Roman", 12), 0)
        self.assertGreater(string_width("Code", "Courier", 12), 0)

    def test_font_module_all_includes_family_helpers(self) -> None:
        expected_exports = {
            "add_fallback_font_family",
            "get_fallback_font_families",
            "get_font_family",
            "set_default_font_family",
            "set_fallback_font_families",
            "shaped_string_width",
        }

        self.assertTrue(expected_exports.issubset(set(font_module.__all__)))

    def test_advanced_typography_measures_fallback_runs(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        original_fallbacks = list(get_fallback_fonts())
        register_font("TestAdvancedFallbackNaskh", font_dir / "NotoNaskhArabic-Medium.ttf")
        register_font("TestAdvancedFallbackSourceHan", font_dir / "SourceHanSansSC-Normal.ttf")
        set_fallback_fonts(["TestAdvancedFallbackSourceHan"])
        try:
            text = "مرحبا中文"
            runs = resolve_text_runs(text, "TestAdvancedFallbackNaskh")
            self.assertEqual([(run.text, run.font_name) for run in runs], [("مرحبا", "TestAdvancedFallbackNaskh"), ("中文", "TestAdvancedFallbackSourceHan")])
            expected_width = shaped_string_width("مرحبا", "TestAdvancedFallbackNaskh", 14) + shaped_string_width("中文", "TestAdvancedFallbackSourceHan", 14)

            self.assertAlmostEqual(shaped_string_width(text, "TestAdvancedFallbackNaskh", 14), expected_width, places=3)
        finally:
            _ = set_fallback_fonts(original_fallbacks)

    def test_table_measurement_uses_registry_string_width(self) -> None:
        self.assertIs(table_model_module._string_width_fn(), string_width)

    def test_font_family_registration_sets_default_and_fallback(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        original_font = get_font().name
        original_fallbacks = list(get_fallback_fonts())
        original_family_fallbacks = list(get_fallback_font_families())
        try:
            family = register_font_family(
                "TestNotoNaskhFamily",
                regular=font_dir / "NotoNaskhArabic-Medium.ttf",
                bold=font_dir / "NotoNaskhArabic-Bold.ttf",
                set_default=True,
                fallback=True,
            )

            self.assertEqual(family.regular, "TestNotoNaskhFamily")
            self.assertEqual(family.bold, "TestNotoNaskhFamily-Bold")
            self.assertEqual(get_font_family("TestNotoNaskhFamily").regular, "TestNotoNaskhFamily")
            self.assertEqual(Style().font_name, "TestNotoNaskhFamily")
            self.assertIn("TestNotoNaskhFamily", get_fallback_font_families())
        finally:
            _ = set_default_font(original_font)
            _ = set_fallback_fonts(original_fallbacks)
            _ = set_fallback_font_families(original_family_fallbacks)

    def test_font_family_builder_selects_registered_regular_face(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font_family("TestBuilderNaskh", regular=font_dir / "NotoNaskhArabic-Medium.ttf")

        text = Text("مرحبا").font_family("TestBuilderNaskh").typography("advanced").text_direction("rtl")

        self.assertEqual(text.node.style.font_family, "TestBuilderNaskh")
        self.assertEqual(text.node.style.font_name, "TestBuilderNaskh")
        self.assertEqual(text.node.style.typography, "advanced")

    def test_advanced_typography_uses_harfbuzz_widths(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestAdvancedNaskh", font_dir / "NotoNaskhArabic-Medium.ttf")

        raw_width = string_width("مرحبا", "TestAdvancedNaskh", 14)
        shaped_width = shaped_string_width("مرحبا", "TestAdvancedNaskh", 14)

        self.assertGreater(shaped_width, 0)
        self.assertNotEqual(round(raw_width, 3), round(shaped_width, 3))

    def test_wrap_text_advanced_uses_harfbuzz_measurement(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestWrapAdvancedNaskh", font_dir / "NotoNaskhArabic-Medium.ttf")
        shaped_width = shaped_string_width("مرحبا", "TestWrapAdvancedNaskh", 14)

        lines = wrap_text("مرحبا", shaped_width - 0.01, "TestWrapAdvancedNaskh", 14, typography="advanced", text_direction="rtl")

        self.assertGreater(len(lines), 1)

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

    def test_text_builder_stores_alignment(self) -> None:
        text = Text("Centered").align("center")

        self.assertEqual(text.node.content["align"], "center")

    def test_text_builder_rejects_unsupported_alignment(self) -> None:
        with self.assertRaises(ValueError):
            _ = Text("Nope").align("justify")

    def test_paint_text_passes_alignment_to_adapter(self) -> None:
        text = Text("Centered").align("center").width(100)
        text.node.resolved_width = 100
        text.node.resolved_height = 20
        adapter = _SpyAdapter()

        paint_text(cast(ReportLabCanvasAdapter, adapter), RenderItem(text.node, Rect(10, 20, 100, 20), (), (0,)))

        self.assertEqual(adapter.text_kwargs[0]["align"], "center")

    def test_adapter_draw_text_offsets_centered_lines(self) -> None:
        fake_canvas = _FakeCanvas()
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.draw_text(
            x=10,
            y=10,
            width=100,
            text="Hi",
            font_name="Helvetica",
            font_size=10,
            line_height=12,
            color=None,
            align="center",
        )

        expected_x = 10 + ((100 - string_width("Hi", "Helvetica", 10)) / 2)
        self.assertAlmostEqual(fake_canvas.text_object.origins[0][0], expected_x, places=3)

    def test_table_cell_boxes_carry_typography_options(self) -> None:
        table = Table([["Label", "مرحبا"]]).typography("auto").text_direction("rtl")
        table.node.resolved_width = 200

        boxes = table_cell_boxes(table.node, 0, 0, 200, table_height(table.node))

        self.assertTrue(all(box.typography == "auto" for box in boxes))
        self.assertTrue(all(box.text_direction == "rtl" for box in boxes))

    def test_adapter_draw_text_emits_shaped_text_for_auto_typography(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestNotoNaskhArabic-Medium", font_dir / "NotoNaskhArabic-Medium.ttf")
        fake_canvas = _FakeCanvas()
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        adapter._canvas = fake_canvas
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

        output = "".join(fake_canvas.text_object.output)
        self.assertNotEqual(output, "مرحبا")
        self.assertTrue(any("\ufe70" <= character <= "\ufeff" for character in output))
        self.assertIn("TestNotoNaskhArabic-Medium", fake_canvas.text_object.font_names)
        self.assertNotIn("Helvetica", fake_canvas.text_object.font_names)

    def test_arabic_font_supports_shaped_presentation_forms(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font("TestNotoNaskhArabic-Support", font_dir / "NotoNaskhArabic-Medium.ttf")

        shaped = shape_text("مرحبا", "auto", "rtl")
        runs = resolve_text_runs(shaped, "TestNotoNaskhArabic-Support")

        self.assertEqual({run.font_name for run in runs}, {"TestNotoNaskhArabic-Support"})

    def test_rect_builder_supports_plain_text_label_api(self) -> None:
        rect = RectBuilder("Paid").align("right").valign("bottom").letter_spacing("5%").text_overflow("clip")

        self.assertEqual(rect.node.content["text"], "Paid")
        self.assertEqual(rect.node.content["align"], "right")
        self.assertEqual(rect.node.content["valign"], "bottom")
        self.assertEqual(rect.node.content["letter_spacing"], "5%")
        self.assertEqual(rect.node.content["text_overflow"], "clip")
        self.assertIs(rect.text(None), rect)
        self.assertNotIn("text", rect.node.content)
        with self.assertRaises(ValueError):
            _ = RectBuilder("Nope").align("justify")
        with self.assertRaises(ValueError):
            _ = RectBuilder("Nope").valign("baseline")
        with self.assertRaises(ValueError):
            _ = RectBuilder("Nope").text_overflow("fade")

    def test_container_add_rect_accepts_text_label(self) -> None:
        frame = Frame()
        add_rect = cast(Any, frame.add_rect)
        rect = add_rect("New")

        self.assertEqual(rect.node.content["text"], "New")
        self.assertIs(frame.node.children[0], rect.node)

    def test_text_rect_auto_sizes_to_label_and_padding(self) -> None:
        rect = RectBuilder("Paid").font("Helvetica").font_size(10).line_height(12).padding(vertical=3, horizontal=8)

        resolve_widths(rect.node, 200)
        resolve_heights(rect.node)

        self.assertAlmostEqual(rect.node.resolved_width, string_width("Paid", "Helvetica", 10) + 16, places=3)
        self.assertEqual(rect.node.resolved_height, 18)

    def test_paint_rect_draws_background_before_centered_label(self) -> None:
        rect = RectBuilder("Paid").size(60, 20).padding(horizontal=6).background("#dcfce7").color("#166534").font("Helvetica").font_size(10).line_height(12).radius(10)
        rect.node.resolved_width = 60
        rect.node.resolved_height = 20
        adapter = _SpyAdapter()

        paint_render_item(cast(ReportLabCanvasAdapter, adapter), RenderItem(rect.node, Rect(5, 7, 60, 20), (), (0,)))

        self.assertEqual(adapter.rects, [Rect(5, 7, 60, 20)])
        self.assertEqual(adapter.texts, ["Paid"])
        self.assertEqual(adapter.text_kwargs[0]["align"], "center")
        self.assertEqual(adapter.text_kwargs[0]["valign"], "middle")
        self.assertEqual(adapter.text_kwargs[0]["x"], 11)
        self.assertEqual(adapter.text_kwargs[0]["width"], 48)
        self.assertEqual(len(adapter.clip_rects), 1)

    def test_text_rect_pagination_is_atomic_but_plain_rect_still_splits(self) -> None:
        text_rect = RectBuilder("Paid").size(80, 40)
        text_rect.node.resolved_width = 80
        text_rect.node.resolved_height = 40
        plain_rect = RectBuilder().size(80, 40)
        plain_rect.node.resolved_width = 80
        plain_rect.node.resolved_height = 40

        self.assertEqual(len(_split_flow_child(text_rect.node, 20, 20)), 1)
        self.assertGreater(len(_split_flow_child(plain_rect.node, 20, 20)), 1)

    def test_rounded_table_painter_clips_cells_and_strokes_outer_radius(self) -> None:
        table = Table([["H1", "H2"], ["A", "B"]]).radius(12).stroke("#94a3b8", 1).background("#ffffff")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        item = RenderItem(table.node, Rect(10, 20, 200, table.node.resolved_height), (), (0,))
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), item)

        self.assertEqual(adapter.rounded_clips, [(10, 20, 200, table.node.resolved_height, CornerRadii.all(12))])
        self.assertIn(CornerRadii.all(12), adapter.drawn_radii)


    def test_radius_supports_individual_corners_and_clone_preserves_them(self) -> None:
        image = Image(_png_bytes(8, 8)).radius((1, 2, 3, 4))
        frame = Frame().radius(top_left=5, bottom_right=7)

        self.assertEqual(image.node.style.border_radius, CornerRadii(1, 2, 3, 4))
        self.assertEqual(frame.node.style.border_radius, CornerRadii(5, 0, 7, 0))
        self.assertEqual(clone_layout_node(image.node).style.border_radius, CornerRadii(1, 2, 3, 4))
        with self.assertRaises(ValueError):
            Image(_png_bytes(8, 8)).radius((1, 2, 3))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            Image(_png_bytes(8, 8)).radius(1, top_left=2)
        with self.assertRaises(ValueError):
            Image(_png_bytes(8, 8)).radius(-1)

    def test_column_widths_support_fixed_percent_and_auto(self) -> None:
        table = Table([["A", "B", "C"]]).column_widths([80, "50%", "auto"])
        table.node.resolved_width = 300
        self.assertEqual(table_column_widths(table.node, 300, 3), [80.0, 150.0, 70.0])

    def test_column_widths_scale_down_when_overflowing(self) -> None:
        table = Table([["A", "B"]]).column_widths([240, 240])
        table.node.resolved_width = 300
        self.assertEqual(table_column_widths(table.node, 300, 2), [150.0, 150.0])

    def test_plain_cell_natural_width_includes_padding_not_border(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(len(text) * 3)

        box = TableCellBox(
            row_index=0,
            source_row_index=0,
            column_index=0,
            x=0,
            y=0,
            width=120,
            height=24,
            text="wide",
            rich_content=None,
            align="left",
            background=None,
            color=None,
            font_name="Helvetica",
            font_size=12,
            line_height=14,
            typography="plain",
            text_direction="auto",
            padding=Edges(top=2, right=5, bottom=2, left=5),
            border_width=9,
        )

        self.assertEqual(table_cell_box_natural_width(box, fixed_width), 22.0)

    def test_plain_cell_natural_width_uses_widest_explicit_line(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(len(text))

        width = plain_cell_natural_width("short\nwidest line\nmid", Edges(top=2, right=3, bottom=2, left=3), "Helvetica", 12, string_width=fixed_width)

        self.assertEqual(width, 17.0)

    def test_plain_cell_natural_width_preserves_spaces_on_non_empty_lines(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(len(text))

        width = plain_cell_natural_width(" A ", Edges(top=1, right=4, bottom=1, left=4), "Helvetica", 12, string_width=fixed_width)

        self.assertEqual(width, 11.0)

    def test_plain_cell_natural_width_whitespace_contributes_padding_only(self) -> None:
        def fixed_width(text: str, font_name: str, font_size: float) -> float:
            _ = (text, font_name, font_size)
            return 999.0

        width = plain_cell_natural_width("  \n\t", Edges(top=1, right=4, bottom=1, left=4), "Helvetica", 12, string_width=fixed_width)

        self.assertEqual(width, 8.0)

    def test_plain_cell_natural_width_excludes_rich_cells(self) -> None:
        padding = Edges(top=1, right=4, bottom=1, left=4)

        self.assertIsNone(plain_cell_natural_width(Frame().add_text("rich").node, padding, "Helvetica", 12))

    def test_column_min_and_max_widths_are_chainable_and_stored(self) -> None:
        table = Table([["A", "B"]])

        result = table.column_min_widths([40, "25%"]).column_max_widths([120, "75%"])

        self.assertIs(result, table)
        self.assertEqual(table.node.content["column_min_widths"], [40, "25%"])
        self.assertEqual(table.node.content["column_max_widths"], [120, "75%"])

    def test_column_min_widths_clamp_and_redistribute_deficit(self) -> None:
        table = Table([["A", "B", "C"]]).column_widths([50, 125, 125]).column_min_widths([90])

        self.assertEqual(table_column_widths(table.node, 300, 3), [90.0, 105.0, 105.0])

    def test_column_max_widths_clamp_and_redistribute_surplus(self) -> None:
        table = Table([["A", "B", "C"]]).column_widths([160, 70, 70]).column_max_widths([120])

        self.assertEqual(table_column_widths(table.node, 300, 3), [120.0, 90.0, 90.0])

    def test_column_width_constraints_support_fixed_percent_and_auto_base_widths(self) -> None:
        table = (
            Table([["A", "B", "C"]])
            .column_widths(["auto", "50%", 120])
            .column_min_widths([90, "40%"])
            .column_max_widths([140, "45%", 130])
        )

        self.assertEqual(table_column_widths(table.node, 300, 3), [90.0, 120.0, 90.0])

    def test_column_width_constraints_preserve_no_constraint_behavior(self) -> None:
        unconstrained = Table([["A", "B", "C"]]).column_widths([240, 240, "auto"])
        constrained_absent = Table([["A", "B", "C"]]).column_widths([240, 240, "auto"])

        self.assertEqual(table_column_widths(constrained_absent.node, 300, 3), table_column_widths(unconstrained.node, 300, 3))

    def test_column_width_constraints_reject_auto_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "column_min_widths.*auto"):
            Table([["A"]]).column_min_widths(["auto"])

        with self.assertRaisesRegex(ValueError, "column_max_widths.*auto"):
            Table([["A"]]).column_max_widths(["auto"])

    def test_column_width_constraints_reject_negative_and_non_finite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "column_min_widths.*non-negative"):
            Table([["A"]]).column_min_widths([-1])

        with self.assertRaisesRegex(ValueError, "column_max_widths.*finite"):
            Table([["A"]]).column_max_widths([float("inf")])

    def test_column_width_constraints_reject_min_greater_than_max(self) -> None:
        table = Table([["A", "B"]]).column_min_widths([100, "60%"]).column_max_widths([90, "50%"])

        with self.assertRaisesRegex(ValueError, "minimum.*maximum"):
            _ = table_column_widths(table.node, 200, 2)

    def test_column_width_constraints_reject_impossible_min_total(self) -> None:
        table = Table([["A", "B"]]).column_min_widths([160, 160])

        with self.assertRaisesRegex(ValueError, "minimum.*exceed"):
            _ = table_column_widths(table.node, 300, 2)

    def test_column_width_constraints_reject_impossible_max_total(self) -> None:
        table = Table([["A", "B"]]).column_max_widths([120, "50%"])

        with self.assertRaisesRegex(ValueError, "maximum.*less"):
            _ = table_column_widths(table.node, 300, 2)

    def test_auto_fit_columns_all_columns_is_chainable_and_stored(self) -> None:
        table = Table([["A", "B"]])

        result = table.auto_fit_columns()

        self.assertIs(result, table)
        self.assertIs(table.node.content["auto_fit_columns"], True)

    def test_auto_fit_columns_selected_indexes_are_stored_deterministically(self) -> None:
        table = Table([["A", "B", "C"]])

        result = table.auto_fit_columns([2, 0])

        self.assertIs(result, table)
        self.assertEqual(table.node.content["auto_fit_columns"], [0, 2])

    def test_auto_fit_columns_rejects_negative_indexes(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto_fit_columns.*non-negative"):
            Table([["A"]]).auto_fit_columns([-1])

    def test_auto_fit_columns_rejects_non_integer_indexes(self) -> None:
        with self.assertRaisesRegex(TypeError, "auto_fit_columns.*integer"):
            Table([["A"]]).auto_fit_columns(cast(Sequence[int], ["0"]))

    def test_auto_fit_columns_does_not_change_legacy_auto_width_equal_share(self) -> None:
        legacy = Table([["A", "B"]]).column_widths(["auto", "auto"])

        self.assertEqual(table_column_widths(legacy.node, 200, 2), [100.0, 100.0])

    def test_auto_fit_columns_all_columns_uses_plain_header_body_and_footer_cells(self) -> None:
        table = Table([["H", "Header"], ["bodywide", "B"]]).footer([["F", "footerwide"]]).auto_fit_columns()

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 2)

        self.assertEqual(widths, [20.0, 22.0])

    def test_auto_fit_columns_selected_indexes_fit_only_selected_columns(self) -> None:
        table = Table([["H0", "H1", "H2"], ["wide0", "legacy", "wider2"]]).column_widths(["auto", "auto", "auto"]).auto_fit_columns([0, 2])

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 3)

        self.assertEqual(widths, [17.0, 265.0, 18.0])

    def test_auto_fit_columns_keeps_selected_fixed_and_percent_columns_authoritative(self) -> None:
        table = Table([["fixed column is much wider", "percent column is wider", "fit"]]).column_widths([80, "50%", "auto"]).auto_fit_columns([0, 1, 2])

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 3)

        self.assertEqual(widths, [80.0, 150.0, 15.0])

    def test_auto_fit_columns_unselected_legacy_auto_columns_share_remaining_width(self) -> None:
        table = Table([["fit", "legacy one", "legacy two"]]).column_widths(["auto", "auto", "auto"]).auto_fit_columns([0])

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 3)

        self.assertEqual(widths, [15.0, 142.5, 142.5])

    def test_auto_fit_columns_applies_min_max_constraints_after_natural_widths(self) -> None:
        table = (
            Table([["tiny", "wide natural"]])
            .auto_fit_columns()
            .column_min_widths([30])
            .column_max_widths([999, 18])
        )

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 2)

        self.assertEqual(widths, [30.0, 18.0])

    def test_auto_fit_columns_clamps_max_before_overflow_compression(self) -> None:
        table = Table([["wide", "x"]]).header(0).cell_padding(0).auto_fit_columns().column_max_widths([150])

        def fake_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return {"wide": 300.0, "x": 10.0}.get(text, float(len(text)))

        with _patched_table_string_width(fake_width):
            widths = table_column_widths(table.node, 200, 2)

        self.assertEqual(widths, [150.0, 10.0])

    def test_auto_fit_columns_allows_max_total_less_than_table_width(self) -> None:
        table = Table([["a", "bb"]]).header(0).cell_padding(0).auto_fit_columns().column_max_widths([10, 10])

        def fake_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return {"a": 12.0, "bb": 25.0}.get(text, float(len(text)))

        with _patched_table_string_width(fake_width):
            widths = table_column_widths(table.node, 300, 2)

        self.assertEqual(widths, [10.0, 10.0])

    def test_auto_fit_columns_rejects_out_of_range_selected_indexes_during_width_resolution(self) -> None:
        table = Table([["A", "B"]]).auto_fit_columns([2])

        with self.assertRaisesRegex(ValueError, "auto_fit_columns.*range"):
            _ = table_column_widths(table.node, 200, 2)

    def test_auto_fit_columns_repeated_layout_calls_are_idempotent(self) -> None:
        rows = [["H0", "H1", "H2"], ["short", "a much wider value", "tail"], ["later", "mid", "longer tail value"]]
        table = Table(rows).header(1).cell_padding(vertical=2, horizontal=3).font_size(10).line_height(12).auto_fit_columns()
        table.node.resolved_width = 300

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            first_widths = table_column_widths(table.node, 300, 3)
            first_height = table_height(table.node)
            first_boxes = table_cell_boxes(table.node, 0, 0, 300, first_height)
            second_height = table_height(table.node)
            second_boxes = table_cell_boxes(table.node, 0, 0, 300, second_height)
            second_widths = table_column_widths(table.node, 300, 3)

        self.assertEqual(second_widths, first_widths)
        self.assertEqual(second_height, first_height)
        self.assertEqual(
            [(box.source_row_index, box.column_index, box.x, box.width) for box in second_boxes],
            [(box.source_row_index, box.column_index, box.x, box.width) for box in first_boxes],
        )

    def test_auto_fit_columns_natural_width_ignores_plain_overflow_mode(self) -> None:
        text = "one two three four five six seven eight"
        tables = [
            Table([[text]]).header(0).cell_padding(vertical=2, horizontal=5).text_overflow(mode).auto_fit_columns()
            for mode in ("wrap", "clip", "ellipsis")
        ]

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text) * 2)):
            widths = [table_column_widths(table.node, 500, 1) for table in tables]

        self.assertEqual(widths, [[88.0], [88.0], [88.0]])

    def test_auto_fit_columns_measures_cjk_and_long_unbroken_words_deterministically(self) -> None:
        rows = [["中文没有空格", "short"], ["tiny", "supercalifragilistic"]]
        table = Table(rows).header(0).cell_padding(vertical=0, horizontal=2).auto_fit_columns()

        def fake_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(sum(10 if "\u4e00" <= character <= "\u9fff" else 1 for character in text))

        with _patched_table_string_width(fake_width):
            widths = table_column_widths(table.node, 500, 2)

        self.assertEqual(widths, [64.0, 24.0])

    def test_auto_fit_columns_uses_widest_explicit_line(self) -> None:
        table = Table([["short\nwidest explicit line\nmid"]]).header(0).cell_padding(vertical=1, horizontal=3).auto_fit_columns()

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 300, 1)

        self.assertEqual(widths, [26.0])

    def test_auto_fit_columns_advanced_typography_uses_shaped_width(self) -> None:
        measured: list[str] = []
        original = table_model_module.shaped_string_width

        def fake_shaped_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            measured.append(text)
            return float(len(text) * 4)

        table = Table([["مرحبا"]]).header(0).cell_padding(vertical=0, horizontal=2).typography("advanced").text_direction("rtl").auto_fit_columns()
        table_model_module.shaped_string_width = fake_shaped_width
        try:
            widths = table_column_widths(table.node, 300, 1)
        finally:
            table_model_module.shaped_string_width = original

        self.assertEqual(widths, [24.0])
        self.assertEqual(measured, ["مرحبا"])

    def test_auto_fit_columns_measures_text_rich_text_and_simple_frame_cells(self) -> None:
        rich_text = RichText().span("small").br().span("rich widest")
        rich_frame = Frame().padding(2)
        rich_frame.add_text("frame wide").margin(left=3, right=5)
        table = (
            Table([[Text("text widest").padding(left=1, right=2).node, rich_text.node, rich_frame.node], ["x", "y", "z"]])
            .header(0)
            .cell_padding(vertical=0, horizontal=4)
            .auto_fit_columns()
        )

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 500, 3)

        self.assertEqual(widths[0], 22.0)
        self.assertAlmostEqual(widths[1], string_width("rich widest", "Helvetica", 12) + 8.0, places=3)
        self.assertEqual(widths[2], 30.0)

    def test_auto_fit_columns_overflow_modes_keep_same_natural_width(self) -> None:
        text = "one two three four"
        widths_by_mode: dict[str, list[float]] = {}

        for mode in ("wrap", "clip", "ellipsis"):
            table = Table([[text]]).header(0).cell_padding(0).text_overflow(mode).auto_fit_columns()
            with _patched_table_string_width(lambda value, font_name, font_size: float(len(value))):
                widths_by_mode[mode] = table_column_widths(table.node, 500, 1)

        self.assertEqual(widths_by_mode["wrap"], [float(len(text))])
        self.assertEqual(widths_by_mode["clip"], widths_by_mode["wrap"])
        self.assertEqual(widths_by_mode["ellipsis"], widths_by_mode["wrap"])

    def test_auto_fit_columns_cjk_and_long_words_have_deterministic_natural_widths(self) -> None:
        rows = [["中文没有空格", "superlongword"]]
        table = Table(rows).header(0).cell_padding(vertical=0, horizontal=2).auto_fit_columns()

        def fake_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            return float(sum(10 if ord(character) > 127 else 3 for character in text))

        with _patched_table_string_width(fake_width):
            widths = table_column_widths(table.node, 500, 2)

        self.assertEqual(widths, [64.0, 43.0])

    def test_auto_fit_columns_advanced_typography_uses_raw_shaped_measurement(self) -> None:
        measured: list[str] = []
        original = table_model_module.shaped_string_width

        def fake_shaped_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            measured.append(text)
            return float(len(text) * 11)

        table = Table([["مرحبا"]]).header(0).cell_padding(vertical=0, horizontal=3).typography("advanced").text_direction("rtl").auto_fit_columns()
        table_model_module.shaped_string_width = fake_shaped_width
        try:
            widths = table_column_widths(table.node, 500, 1)
        finally:
            table_model_module.shaped_string_width = original

        self.assertEqual(widths, [61.0])
        self.assertEqual(measured, ["مرحبا"])

    def test_auto_fit_columns_explicit_newlines_use_widest_line_and_empty_padding_only(self) -> None:
        table = Table([["tiny\nwidest", "   \n\t"]]).header(0).cell_padding(vertical=0, horizontal=5).auto_fit_columns()

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text) * 4)):
            widths = table_column_widths(table.node, 500, 2)

        self.assertEqual(widths, [34.0, 10.0])

    def test_auto_fit_columns_ignores_unsupported_rich_cells_conservatively(self) -> None:
        image = Image(_png_bytes(16, 16))
        frame_with_image = Frame().padding(0)
        frame_with_image.add_image(_png_bytes(16, 16))
        absolute_frame = Frame().padding(0)
        absolute_frame.add_text("absolute wide").absolute(0, 0)
        flex_frame = Frame().flex("row").padding(0)
        flex_frame.add_text("flex wide")
        table = (
            Table([[image.node, frame_with_image.node, absolute_frame.node, flex_frame.node], ["a", "bb", "ccc", "dddd"]])
            .header(0)
            .cell_padding(vertical=0, horizontal=1)
            .auto_fit_columns()
        )

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            widths = table_column_widths(table.node, 500, 4)

        self.assertEqual(widths, [3.0, 4.0, 5.0, 6.0])

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

    def test_table_font_overflow_and_valign_styles_follow_precedence(self) -> None:
        table = (
            Table([["A", "B"], ["C", "D"], ["E", "F"]])
            .header(0)
            .column_widths([120, 120])
            .font("Helvetica")
            .font_size(10)
            .line_height(12)
            .text_overflow("clip")
            .valign("middle")
            .column_style(1, font="Courier", font_size=11, line_height=13, text_overflow="ellipsis", valign="bottom")
            .row_style(1, font="Times-Roman", font_size=12, line_height=14, text_overflow="wrap", valign="top")
            .cell_style(2, 1, font="Helvetica-Bold", font_size=15, line_height=17, text_overflow="clip", valign="middle")
        )
        table.node.resolved_width = 240

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        default_box = next(box for box in boxes if box.source_row_index == 0 and box.column_index == 0)
        column_box = next(box for box in boxes if box.source_row_index == 0 and box.column_index == 1)
        row_box = next(box for box in boxes if box.source_row_index == 1 and box.column_index == 1)
        cell_box = next(box for box in boxes if box.source_row_index == 2 and box.column_index == 1)

        self.assertEqual((default_box.font_name, default_box.font_size, default_box.line_height), ("Helvetica", 10, 12))
        self.assertEqual((default_box.text_overflow, default_box.valign), ("clip", "middle"))
        self.assertEqual((column_box.font_name, column_box.font_size, column_box.line_height), ("Courier", 11, 13))
        self.assertEqual((column_box.text_overflow, column_box.valign), ("ellipsis", "bottom"))
        self.assertEqual((row_box.font_name, row_box.font_size, row_box.line_height), ("Times-Roman", 12, 14))
        self.assertEqual((row_box.text_overflow, row_box.valign), ("wrap", "top"))
        self.assertEqual((cell_box.font_name, cell_box.font_size, cell_box.line_height), ("Helvetica-Bold", 15, 17))
        self.assertEqual((cell_box.text_overflow, cell_box.valign), ("clip", "middle"))

    def test_plain_cell_clip_and_ellipsis_measure_as_one_line(self) -> None:
        text = "one two three four five six seven eight"
        wrap_table = Table([[text]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12)
        clip_table = Table([[text]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12).text_overflow("clip")
        ellipsis_table = Table([[text]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12).text_overflow("ellipsis")
        for table in (wrap_table, clip_table, ellipsis_table):
            table.node.resolved_width = 60

        self.assertGreater(table_height(wrap_table.node), 24)
        self.assertEqual(table_height(clip_table.node), 24)
        self.assertEqual(table_height(ellipsis_table.node), 24)

    def test_wrap_overflow_keeps_existing_plain_cell_wrapping(self) -> None:
        text = "one two three four five six seven eight"
        default_table = Table([[text]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12)
        wrap_table = Table([[text]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12).text_overflow("wrap")
        default_table.node.resolved_width = 60
        wrap_table.node.resolved_width = 60

        self.assertEqual(table_height(wrap_table.node), table_height(default_table.node))

    def test_plain_cell_clip_normalizes_newlines_when_painted(self) -> None:
        table = Table([["alpha\nbeta\rgamma"]]).header(0).column_widths([200]).cell_padding(0).text_overflow("clip")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        self.assertEqual(adapter.texts, ["alpha beta gamma"])

    def test_plain_cell_ellipsis_paints_longest_fitting_prefix(self) -> None:
        text = "Revenue exceeded expectations"
        table = Table([[text]]).header(0).column_widths([80]).cell_padding(0).font("Helvetica").font_size(12).line_height(14).text_overflow("ellipsis")
        table.node.resolved_width = 80
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 80, table.node.resolved_height), (), (0,)))

        rendered = adapter.texts[0]
        self.assertTrue(rendered.endswith("…"))
        self.assertTrue(text.startswith(rendered[:-1]))
        self.assertLessEqual(string_width(rendered, "Helvetica", 12), 80)
        self.assertGreater(string_width(rendered[:-1] + text[len(rendered) - 1:len(rendered)] + "…", "Helvetica", 12), 80)

    def test_plain_cell_ellipsis_normalizes_newlines_before_fitting(self) -> None:
        table = Table([["alpha\nbeta gamma"]]).header(0).column_widths([70]).cell_padding(0).font("Helvetica").font_size(12).line_height(14).text_overflow("ellipsis")
        table.node.resolved_width = 70
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 70, table.node.resolved_height), (), (0,)))

        self.assertNotIn("\n", adapter.texts[0])
        self.assertNotIn("\r", adapter.texts[0])
        self.assertTrue(adapter.texts[0].startswith("alpha "))

    def test_plain_cell_ellipsis_handles_cjk_and_unbroken_words(self) -> None:
        rows = [["中文没有空格也应该省略"], ["supercalifragilisticexpialidocious"]]
        table = Table(rows).header(0).column_widths([64]).cell_padding(0).font("Helvetica").font_size(12).line_height(14).text_overflow("ellipsis")
        table.node.resolved_width = 64
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 64, table.node.resolved_height), (), (0,)))

        self.assertEqual(len(adapter.texts), 2)
        self.assertTrue(all(text.endswith("…") for text in adapter.texts))
        self.assertTrue(all(string_width(text, "Helvetica", 12) <= 64 for text in adapter.texts))

    def test_plain_cell_ellipsis_omits_too_wide_ellipsis(self) -> None:
        table = Table([["abcdef"]]).header(0).column_widths([1]).cell_padding(0).font("Helvetica").font_size(12).line_height(14).text_overflow("ellipsis")
        table.node.resolved_width = 1
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 1, table.node.resolved_height), (), (0,)))

        self.assertEqual(adapter.texts, [""])

    def test_paint_text_multiline_ellipsis_uses_fixed_height_lines(self) -> None:
        text = Text("one two three four five six seven").size(78, 24).font("Helvetica").font_size(10).line_height(12).text_overflow("ellipsis")
        text.node.resolved_width = 78
        text.node.resolved_height = 24
        adapter = _SpyAdapter()

        paint_text(cast(ReportLabCanvasAdapter, adapter), RenderItem(text.node, Rect(0, 0, 78, 24), (), (0,)))

        rendered_lines = adapter.texts[0].split("\n")
        self.assertEqual(len(rendered_lines), 2)
        self.assertTrue(rendered_lines[-1].endswith("…"))
        self.assertEqual(adapter.text_kwargs[0]["lines"], rendered_lines)
        self.assertEqual(len(adapter.clip_rects), 1)

    def test_text_multiline_ellipsis_links_visible_lines_only(self) -> None:
        text = Text("one two three four five six seven").size(78, 24).font("Helvetica").font_size(10).line_height(12).text_overflow("ellipsis").link("https://example.com")
        text.node.resolved_width = 78
        text.node.resolved_height = 24
        adapter = _SpyAdapter()

        paint_text(cast(ReportLabCanvasAdapter, adapter), RenderItem(text.node, Rect(10, 20, 78, 24), (), (0,)))

        self.assertEqual([url for url, _rect in adapter.links], ["https://example.com", "https://example.com"])
        self.assertEqual([rect.y for _url, rect in adapter.links], [20, 32])

    def test_text_ellipsis_pagination_keeps_fixed_box_atomic(self) -> None:
        value = "one two three four five six seven eight nine"
        text = Text(value).size(48, 24).font_size(10).line_height(12).text_overflow("ellipsis")
        text.node.resolved_width = 48
        text.node.resolved_height = 24

        slices = _split_flow_child(text.node, 12, 800)

        self.assertEqual(len(slices), 1)
        self.assertEqual(slices[0].content["text"], value)
        self.assertEqual(slices[0].resolved_height, 24)

    def test_plain_overflow_width_helpers_use_injected_measurement(self) -> None:
        measured: list[str] = []

        def fake_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            measured.append(text)
            return float(len(text))

        self.assertEqual(plain_overflow_text_width("abcdef", "Helvetica", 12, string_width=fake_width), 6)
        self.assertEqual(fit_plain_overflow_text("abcdef", 4, "Helvetica", 12, string_width=fake_width), "abc…")
        self.assertIn("abc…", measured)

    def test_plain_overflow_advanced_width_uses_raw_text(self) -> None:
        measured: list[str] = []
        original = table_model_module.shaped_string_width

        def fake_shaped_width(text: str, font_name: str, font_size: float) -> float:
            _ = (font_name, font_size)
            measured.append(text)
            return float(len(text))

        table_model_module.shaped_string_width = fake_shaped_width
        try:
            self.assertEqual(plain_overflow_text_width("مرحبا", "Helvetica", 12, typography="advanced", text_direction="rtl"), 5)
        finally:
            table_model_module.shaped_string_width = original

        self.assertEqual(measured, ["مرحبا"])

    def test_rich_cells_ignore_plain_overflow_modes(self) -> None:
        rich = Frame().padding(0)
        rich.add_text("one two three four five six seven eight").font_size(10).line_height(12)
        table = Table([[rich.node]]).header(0).column_widths([60]).cell_padding(0).font_size(10).line_height(12).text_overflow("ellipsis")
        table.node.resolved_width = 60

        boxes = table_cell_boxes(table.node, 0, 0, 60, table_height(table.node))

        self.assertIsNotNone(boxes[0].rich_content)
        self.assertGreater(boxes[0].height, 24)

    def test_footer_style_can_override_font_metrics(self) -> None:
        table = (
            Table([["Metric", "Value"], ["A", "1"]])
            .column_widths([120, 120])
            .font("Helvetica")
            .font_size(10)
            .line_height(12)
            .footer([["Total", "1"]], background="#e2e8f0", color="#111827")
            .footer_style(font="Helvetica-Bold", font_size=16, line_height=20, align="right")
        )
        table.node.resolved_width = 240

        boxes = table_cell_boxes(table.node, 0, 0, 240, table_height(table.node))
        footer_box = next(box for box in boxes if box.source_row_index == 2 and box.column_index == 0)
        body_box = next(box for box in boxes if box.source_row_index == 1 and box.column_index == 0)

        self.assertEqual((footer_box.font_name, footer_box.font_size, footer_box.line_height), ("Helvetica-Bold", 16, 20))
        self.assertEqual(footer_box.align, "right")
        self.assertGreater(footer_box.height, body_box.height)

    def test_invalid_text_overflow_and_valign_raise_early(self) -> None:
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).text_overflow("fade")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).valign("baseline")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).column_style(0, text_overflow="fade")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).row_style(0, valign="baseline")
        with self.assertRaises(ValueError):
            _ = Table([["A"]]).cell_style(0, 0, text_overflow="fade")

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

    def test_row_height_raises_row_above_default_content_height(self) -> None:
        baseline = Table([["A"], ["B"]]).header(0).column_widths([120])
        baseline.node.resolved_width = 120
        baseline_heights = table_row_heights(baseline.node, table_rows(baseline.node), table_column_widths(baseline.node, 120, 1))
        table = Table([["A"], ["B"]]).header(0).column_widths([120]).row_heights([42, None])
        table.node.resolved_width = 120

        row_heights = table_row_heights(table.node, table_rows(table.node), table_column_widths(table.node, 120, 1))

        self.assertGreater(row_heights[0], baseline_heights[0])
        self.assertEqual(row_heights[0], 42.0)
        self.assertEqual(row_heights[1], baseline_heights[1])
        self.assertEqual(table_height(table.node), 42.0 + baseline_heights[1])

    def test_cell_height_raises_row_height_and_box_height(self) -> None:
        table = Table([["A", "B"]]).header(0).column_widths([80, 80]).cell_height(0, 1, 54)
        table.node.resolved_width = 160

        boxes = table_cell_boxes(table.node, 0, 0, 160, table_height(table.node))
        target = next(box for box in boxes if box.column_index == 1)

        self.assertEqual(table_height(table.node), 54.0)
        self.assertEqual(target.height, 54.0)

    def test_content_taller_than_explicit_height_wins(self) -> None:
        text = "one two three four five six seven eight"
        table = Table([[text]]).header(0).column_widths([40]).cell_padding(0).font_size(10).line_height(12).row_height(0, 10)
        table.node.resolved_width = 40

        height = table_height(table.node)

        self.assertGreater(height, 24.0)
        self.assertGreater(height, 10.0)

    def test_invalid_row_and_cell_heights_raise_early(self) -> None:
        invalid_values = ["auto", "50%", -1, float("inf"), float("nan")]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _ = Table([["A"]]).row_height(0, value)
                with self.assertRaises(ValueError):
                    _ = Table([["A"]]).row_heights([value])
                with self.assertRaises(ValueError):
                    _ = Table([["A"]]).cell_height(0, 0, value)

    def test_rowspan_cell_height_distributes_total_height_across_spanned_rows(self) -> None:
        rows = [["Group", "A"], ["", "B"]]
        table = Table(rows).header(0).column_widths([80, 80]).span(0, 0, rowspan=2).cell_height(0, 0, 80)
        table.node.resolved_width = 160

        row_heights = table_row_heights(table.node, rows, table_column_widths(table.node, 160, 2))
        boxes = table_cell_boxes(table.node, 0, 0, 160, table_height(table.node))
        rowspan_box = next(box for box in boxes if box.row_index == 0 and box.column_index == 0)

        self.assertEqual(row_heights, [40.0, 40.0])
        self.assertEqual(rowspan_box.height, 80.0)

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

    def test_plain_cell_vertical_alignment_offsets_text_with_padding(self) -> None:
        tables = [
            Table([["top"]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).font_size(10).line_height(10).valign("top"),
            Table([["middle"]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).font_size(10).line_height(10).valign("middle"),
            Table([["bottom"]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).font_size(10).line_height(10).valign("bottom"),
        ]
        y_positions: list[float] = []
        for table in tables:
            table.node.resolved_width = 100
            table.node.resolved_height = 60
            adapter = _SpyAdapter()

            paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 100, 60), (), (0,)))

            y_value = adapter.text_kwargs[0]["y"]
            self.assertIsInstance(y_value, (int, float))
            y_positions.append(float(cast(float, y_value)))

        self.assertEqual(y_positions, [4.0, 24.0, 44.0])

    def test_plain_cell_valign_does_not_change_measured_height(self) -> None:
        tables = [
            Table([["one two three four five"]]).header(0).column_widths([60]).cell_padding(4).font_size(10).line_height(12).valign(value)
            for value in ("top", "middle", "bottom")
        ]
        for table in tables:
            table.node.resolved_width = 60

        self.assertEqual([table_height(table.node) for table in tables], [table_height(tables[0].node)] * 3)

    def test_rich_cell_vertical_alignment_offsets_unsplit_content(self) -> None:
        rich_cell = Frame().padding(0)
        rich_cell.add_text("Nested").font_size(10).line_height(12)
        tables = [
            Table([[rich_cell]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).valign("top"),
            Table([[rich_cell]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).valign("middle"),
            Table([[rich_cell]]).header(0).column_widths([100]).cell_padding(top=4, right=0, bottom=6, left=0).valign("bottom"),
        ]
        y_positions: list[float] = []
        for table in tables:
            table.node.resolved_width = 100
            table.node.resolved_height = 60
            adapter = _SpyAdapter()

            paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 100, 60), (), (0,)))

            y_value = adapter.text_kwargs[0]["y"]
            self.assertIsInstance(y_value, (int, float))
            y_positions.append(float(cast(float, y_value)))

        self.assertEqual(y_positions, [4.0, 23.0, 42.0])

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

    def test_border_collapse_is_chainable_and_stored(self) -> None:
        table = Table([["A"]])

        result = table.border_collapse()

        self.assertIs(result, table)
        self.assertIs(table.node.content["border_collapse"], True)
        table.border_collapse(False)
        self.assertIs(table.node.content["border_collapse"], False)

    def test_default_border_mode_keeps_separate_cell_painting(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=1)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        internal_vertical = [line for line in adapter.lines if line[0] == line[2] == 100.0]
        internal_horizontal_y = table.node.resolved_height / 2
        internal_horizontal = [line for line in adapter.lines if line[1] == line[3] == internal_horizontal_y]
        self.assertEqual(len(internal_vertical), 4)
        self.assertEqual(len(internal_horizontal), 4)

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

    def test_collapsed_borders_paint_shared_grid_segments_once(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=1).border_collapse()
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        internal_vertical = [line for line in adapter.lines if line[0] == line[2] == 100.0]
        internal_horizontal_y = table.node.resolved_height / 2
        internal_horizontal = [line for line in adapter.lines if line[1] == line[3] == internal_horizontal_y]
        self.assertEqual(len(internal_vertical), 2)
        self.assertEqual(len(internal_horizontal), 2)

    def test_collapsed_borders_split_rowspan_shared_edge_without_overlap(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).span(0, 0, rowspan=2).borders("#111827", width=1).border_collapse()
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        vertical_segments = [line for line in adapter.lines if line[0] == line[2] == 100.0]
        self.assertEqual(
            [(line[1], line[3]) for line in vertical_segments],
            [(0.0, 26.4), (26.4, 52.8)],
        )

    def test_collapsed_borders_split_colspan_shared_edge_without_overlap(self) -> None:
        table = Table([["A", "B"], ["C", "D"]]).span(0, 0, colspan=2).borders("#111827", width=1).border_collapse()
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        internal_horizontal_y = table.node.resolved_height / 2
        horizontal_segments = [line for line in adapter.lines if line[1] == line[3] == internal_horizontal_y]
        self.assertEqual(
            [(line[0], line[2]) for line in horizontal_segments],
            [(0.0, 100.0), (100.0, 200.0)],
        )

    def test_collapsed_border_conflict_prefers_greater_width(self) -> None:
        table = (
            Table([["A", "B"], ["C", "D"]])
            .borders("#111827", width=1)
            .cell_border(0, 0, color="#dc2626", width=1)
            .cell_border(0, 1, color="#2563eb", width=4)
            .border_collapse()
        )
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        top_shared_vertical = next(line for line in adapter.lines if line[0] == line[2] == 100.0 and line[1] == 0.0)
        color = adapter.line_colors[adapter.lines.index(top_shared_vertical)]
        cell_styles = cast(dict[str, dict[str, object]], table.node.content["cell_styles"])
        self.assertEqual(top_shared_vertical[4], 4)
        self.assertEqual(color, cell_styles["0:1"]["border_color"])

    def test_collapsed_border_ties_choose_lower_row_and_right_column(self) -> None:
        table = (
            Table([["A", "B"], ["C", "D"]])
            .borders("#111827", width=1)
            .cell_border(0, 0, color="#dc2626", width=3)
            .cell_border(1, 0, color="#16a34a", width=3)
            .cell_border(0, 1, color="#2563eb", width=3)
            .border_collapse()
        )
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)
        adapter = _SpyAdapter()

        paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table.node, Rect(0, 0, 200, table.node.resolved_height), (), (0,)))

        internal_horizontal_y = table.node.resolved_height / 2
        left_shared_horizontal = next(line for line in adapter.lines if line[:4] == (0.0, internal_horizontal_y, 100.0, internal_horizontal_y))
        top_shared_vertical = next(line for line in adapter.lines if line[0] == line[2] == 100.0 and line[1] == 0.0)
        horizontal_color = adapter.line_colors[adapter.lines.index(left_shared_horizontal)]
        vertical_color = adapter.line_colors[adapter.lines.index(top_shared_vertical)]
        cell_styles = cast(dict[str, dict[str, object]], table.node.content["cell_styles"])
        self.assertEqual(horizontal_color, cell_styles["1:0"]["border_color"])
        self.assertEqual(vertical_color, cell_styles["0:1"]["border_color"])

    def test_collapsed_borders_do_not_affect_table_measurement(self) -> None:
        separate = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=1, inner_width=0.5, outer_width=3)
        collapsed = Table([["A", "B"], ["C", "D"]]).borders("#111827", width=1, inner_width=0.5, outer_width=3).border_collapse()
        separate.node.resolved_width = 200
        collapsed.node.resolved_width = 200

        collapsed_widths = table_column_widths(collapsed.node, 200, 2)
        separate_widths = table_column_widths(separate.node, 200, 2)
        self.assertEqual(collapsed_widths, separate_widths)
        self.assertEqual(table_row_heights(collapsed.node, table_rows(collapsed.node), collapsed_widths), table_row_heights(separate.node, table_rows(separate.node), separate_widths))
        self.assertEqual(table_height(collapsed.node), table_height(separate.node))

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

        self.assertEqual(adapter.rounded_clips, [])
        self.assertEqual(adapter.images[0][1], "contain")
        self.assertEqual(adapter.image_radii, [CornerRadii.all(5)])


    def test_image_mixed_corner_radius_clips_with_corner_radii(self) -> None:
        image_bytes = _png_bytes(16, 8)
        image = Image(image_bytes).cover().radius(top_left=2, top_right=4, bottom_right=6, bottom_left=8).width(80)
        image.node.resolved_width = 80
        image.node.resolved_height = 40
        adapter = _SpyAdapter()

        paint_image(cast(ReportLabCanvasAdapter, adapter), RenderItem(image.node, Rect(10, 20, 80, 40), (), (0,)))

        self.assertEqual(adapter.rounded_clips, [])
        self.assertEqual(adapter.images[0][1], "cover")
        self.assertEqual(adapter.image_radii, [CornerRadii(2, 4, 6, 8)])

    def test_reportlab_adapter_uses_custom_path_for_mixed_corner_radius(self) -> None:
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_rect(Rect(10, 20, 80, 40), fill=parse_color("#ffffff"), radius=CornerRadii(2, 4, 6, 8))

        self.assertEqual(fake_canvas.round_rects, [])
        self.assertEqual(len(fake_canvas.drawn_paths), 1)
        self.assertTrue(any(command[0] == "curveTo" for command in fake_canvas.drawn_paths[0]))

    def test_reportlab_adapter_keeps_uniform_radius_fast_path(self) -> None:
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_rect(Rect(10, 20, 80, 40), fill=parse_color("#ffffff"), radius=CornerRadii.all(5))

        self.assertEqual(fake_canvas.round_rects, [(10, 140, 80, 40, 5, 0, 1)])
        self.assertEqual(fake_canvas.drawn_paths, [])


    def test_reportlab_adapter_contain_image_radius_clips_fitted_rect(self) -> None:
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200
        adapter._image_reader = lambda _source: object()  # type: ignore[method-assign]
        adapter._image_size = lambda _reader: (16.0, 8.0)  # type: ignore[method-assign]

        adapter.draw_image(b"fake", Rect(10, 20, 80, 80), fit="contain", radius=CornerRadii.all(5))

        self.assertEqual(fake_canvas.round_rects, [])
        self.assertEqual(fake_canvas.draw_image_rects, [(10, 120, 80, 40)])
        self.assertIn(("roundRect", 10, 120, 80, 40, 5), fake_canvas.drawn_paths[0])

    def test_reportlab_adapter_cover_image_radius_keeps_outer_crop_and_clips_fitted_rect(self) -> None:
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200
        adapter._image_reader = lambda _source: object()  # type: ignore[method-assign]
        adapter._image_size = lambda _reader: (16.0, 8.0)  # type: ignore[method-assign]

        adapter.draw_image(b"fake", Rect(10, 20, 80, 80), fit="cover", radius=CornerRadii(2, 4, 6, 8))

        self.assertEqual(fake_canvas.draw_image_rects, [(-30, 100, 160, 80)])
        self.assertTrue(any(("rect", 10, 100, 80, 80) in commands for commands in fake_canvas.drawn_paths))
        self.assertTrue(any(any(command[0] == "curveTo" for command in commands) for commands in fake_canvas.drawn_paths))

    def test_image_accepts_path_source_and_normalizes_to_string(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "sample.png"
            image_path.write_bytes(_png_bytes(17, 9))

            image = Image(image_path)

        self.assertEqual(image.node.content["src"], str(image_path))
        self.assertIsInstance(image.node.content["src"], str)
        self.assertEqual(image.node.content["intrinsic_width"], 17.0)
        self.assertEqual(image.node.content["intrinsic_height"], 9.0)

    def test_add_image_accepts_path_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "sample.png"
            image_path.write_bytes(_png_bytes(13, 7))
            frame = Frame()

            image = frame.add_image(image_path)

        self.assertEqual(image.node.content["src"], str(image_path))
        self.assertEqual(frame.node.children[0].content["src"], str(image_path))
        self.assertEqual(image.node.content["intrinsic_width"], 13.0)
        self.assertEqual(image.node.content["intrinsic_height"], 7.0)


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

    def test_auto_fit_pagination_preserves_full_table_widths_with_repeated_headers(self) -> None:
        rows = [["Metric", "Value", "Notes"]]
        rows.extend([[f"Early {index}", "ok", "short"] for index in range(1, 8)])
        rows.append(["Later", "plain text in a later slice is the widest value", "tail"])
        rows.extend([[f"Tail {index}", "ok", "short"] for index in range(9, 16)])
        table = (
            Table(rows)
            .header(background="#0f172a", color="#ffffff", repeat=True)
            .cell_padding(vertical=2, horizontal=3)
            .font_size(10)
            .line_height(12)
            .auto_fit_columns()
        )
        table.node.resolved_width = 500

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            expected_widths = table_column_widths(table.node, 500, 3)
            table.node.resolved_height = table_height(table.node)
            slices = _split_table_node(table.node, 86, 86)
            slice_widths = [table_column_widths(table_slice, table_slice.resolved_width, 3) for table_slice in slices]
            slice_second_column_x = [
                next(box for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height) if box.row_index == 0 and box.column_index == 1).x
                for table_slice in slices
            ]

        self.assertGreater(len(slices), 1)
        self.assertTrue(any(8 in cast(list[int], table_slice.content["source_row_indices"]) for table_slice in slices[1:]))
        self.assertTrue(all(cast(list[list[object]], table_slice.content["rows"])[0] == rows[0] for table_slice in slices))
        self.assertEqual(slice_widths, [expected_widths] * len(slices))
        self.assertEqual(slice_second_column_x, [expected_widths[0]] * len(slices))

    def test_auto_fit_pagination_preserves_rich_content_widths(self) -> None:
        rich = RichText().span("later rich content is widest")
        rows: list[list[object]] = [["Metric", "Value", "Notes"]]
        rows.extend([[f"Early {index}", "ok", "short"] for index in range(1, 8)])
        rows.append(["Later", rich.node, "tail"])
        rows.extend([[f"Tail {index}", "ok", "short"] for index in range(9, 16)])
        table = (
            Table(rows)
            .header(background="#0f172a", color="#ffffff", repeat=True)
            .cell_padding(vertical=2, horizontal=3)
            .font_size(10)
            .line_height(12)
            .auto_fit_columns()
        )
        table.node.resolved_width = 500

        with _patched_table_string_width(lambda text, font_name, font_size: float(len(text))):
            expected_widths = table_column_widths(table.node, 500, 3)
            table.node.resolved_height = table_height(table.node)
            slices = _split_table_node(table.node, 86, 86)
            slice_widths = [table_column_widths(table_slice, table_slice.resolved_width, 3) for table_slice in slices]

        self.assertGreater(len(slices), 1)
        self.assertGreater(expected_widths[1], 12.0)
        self.assertTrue(any(8 in cast(list[int], table_slice.content["source_row_indices"]) for table_slice in slices[1:]))
        self.assertEqual(slice_widths, [expected_widths] * len(slices))


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

    def test_pagination_preserves_logical_row_and_cell_heights_after_slicing(self) -> None:
        rows = self._rows(14)
        table = (
            Table(rows)
            .column_widths([140, 100, 100])
            .header(background="#0f172a", color="#ffffff", repeat=True)
            .row_height(0, 32)
            .row_height(6, 48)
            .cell_height(8, 1, 56)
            .font_size(10)
            .line_height(12)
        )
        table.node.resolved_width = 340
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 104, 104)
        header_heights = []
        row_height_matches = []
        cell_height_matches = []
        for table_slice in slices:
            boxes = table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
            header_heights.append(next(box.height for box in boxes if box.source_row_index == 0 and box.column_index == 0))
            row_height_matches.extend(box.height for box in boxes if box.source_row_index == 6 and box.column_index == 0)
            cell_height_matches.extend(box.height for box in boxes if box.source_row_index == 8 and box.column_index == 1)

        self.assertGreater(len(slices), 1)
        self.assertEqual(header_heights, [32.0] * len(slices))
        self.assertEqual(row_height_matches, [48.0])
        self.assertEqual(cell_height_matches, [56.0])

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
        rich_cell = Frame().padding(0).background("#f8fafc")
        for _ in range(5):
            rich_cell.add(Spacer(20))
        table = (
            Table([["Metric", "Details"], ["Revenue", rich_cell]])
            .column_widths([100, 160])
            .header(background="#1d4ed8", color="#ffffff", repeat=True)
            .footer([["Total", "216K"]], repeat=True, background="#e2e8f0")
            .cell_style(1, 1, background="#dcfce7")
            .cell_padding(vertical=6, horizontal=6)
            .valign("bottom")
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
        self.assertTrue(all(box.valign == "bottom" for box in styled_fragment_boxes))

        painted_fragment_y_positions = []
        for table_slice in slices:
            adapter = _SpyAdapter()
            paint_table(cast(ReportLabCanvasAdapter, adapter), RenderItem(table_slice, Rect(0, 0, table_slice.resolved_width, table_slice.resolved_height), (), (0,)))
            boxes = table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
            detail_box = next((box for box in boxes if box.source_row_index == 1 and box.column_index == 1), None)
            fragment_rects = [rect for rect, fill in zip(adapter.rects, adapter.rect_fills) if fill == rich_cell.node.style.background]
            if detail_box is not None and fragment_rects:
                painted_fragment_y_positions.append(fragment_rects[0].y)
                self.assertAlmostEqual(fragment_rects[0].y, detail_box.y + detail_box.padding.top)

        self.assertGreater(len(painted_fragment_y_positions), 1)

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

    def test_row_with_multiple_rich_frame_cells_splits_across_table_slices(self) -> None:
        first_cell = Frame().padding(0)
        second_cell = Frame().padding(0)
        for _ in range(5):
            first_cell.add(Spacer(20))
            second_cell.add(Spacer(20))
        table = (
            Table([["Left", "Right"], [first_cell, second_cell]])
            .column_widths([130, 130])
            .cell_style(1, 0, background="#dcfce7")
            .cell_style(1, 1, background="#e0f2fe")
            .cell_padding(vertical=6, horizontal=6)
        )
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]
        fragment_indices = [
            fragment
            for table_slice in slices
            for source, fragment in zip(cast(list[int], table_slice.content["source_row_indices"]), cast(list[int], table_slice.content["source_row_fragment_indices"]))
            if source == 1
        ]
        frame_cells: list[object] = []
        styled_fragment_boxes = []
        for table_slice in slices:
            slice_rows = cast(list[list[object]], table_slice.content["rows"])
            slice_source_rows = cast(list[int], table_slice.content["source_row_indices"])
            if 1 in slice_source_rows:
                row = slice_rows[slice_source_rows.index(1)]
                frame_cells.extend([row[0], row[1]])
            styled_fragment_boxes.extend(
                box
                for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height)
                if box.source_row_index == 1 and box.column_index in {0, 1}
            )

        self.assertGreater(source_rows.count(1), 1)
        self.assertEqual(fragment_indices, list(range(len(fragment_indices))))
        self.assertTrue(any(isinstance(cell, LayoutNode) and cell.node_type == "frame" for cell in frame_cells))
        self.assertTrue(all(table_slice.resolved_height <= 70 for table_slice in slices))
        self.assertEqual(len(styled_fragment_boxes), source_rows.count(1) * 2)
        self.assertTrue(all(box.background is not None for box in styled_fragment_boxes))

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

    def test_rich_text_element_table_cell_splits_without_reapplying_min_height(self) -> None:
        rich_text = RichText().font_size(8).line_height(10)
        for index in range(60):
            rich_text.span(f"note-{index} ")
        table = (
            Table([["Metric", "Details"], ["Revenue", rich_text]])
            .column_widths([90, 160])
            .cell_padding(vertical=2, horizontal=4)
            .row_height(1, 78)
            .cell_height(1, 1, 78)
        )
        table.node.resolved_width = 250
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 110, 110)
        detail_boxes = [
            next(box for box in table_cell_boxes(table_slice, 0, 0, table_slice.resolved_width, table_slice.resolved_height) if box.source_row_index == 1 and box.column_index == 1)
            for table_slice in slices
        ]
        fragment_indices = [cast(list[int], table_slice.content["source_row_fragment_indices"])[-1] for table_slice in slices]
        detail_cells = [cast(list[list[object]], table_slice.content["rows"])[-1][1] for table_slice in slices]

        self.assertEqual(fragment_indices, [0, 1])
        self.assertTrue(all(isinstance(cell, LayoutNode) and cell.node_type == "rich_text" for cell in detail_cells))
        self.assertEqual(detail_boxes[0].height, 84.0)
        self.assertEqual(detail_boxes[1].height, 44.0)
        self.assertLess(detail_boxes[1].height, 78.0)


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

    def test_row_with_complex_rich_frame_cell_remains_atomic(self) -> None:
        simple_frame = Frame().padding(0)
        complex_frame = Frame().flex("row").padding(0)
        for _ in range(5):
            simple_frame.add(Spacer(20))
            complex_frame.add(Spacer(20))
        table = Table([["Left", "Right"], [simple_frame, complex_frame]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
        table.node.resolved_width = 260
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 70, 70)
        source_rows = [source for table_slice in slices for source in cast(list[int], table_slice.content["source_row_indices"])]

        self.assertEqual(source_rows.count(1), 1)

    def test_single_complex_rich_frame_cells_remain_atomic(self) -> None:
        cases = []
        flex_frame = Frame().flex("row", wrap=True).padding(0)
        grid_frame = Frame().grid(2).padding(0)
        columns_frame = Frame().columns(2).padding(0)
        image_frame = Frame().padding(0)
        image_frame.add_image(_png_bytes(16, 40)).size(40, 100)
        absolute_frame = Frame().padding(0)
        absolute_frame.add_text("absolute").absolute(0, 0)
        cases.extend([flex_frame, grid_frame, columns_frame, image_frame, absolute_frame])
        for rich_frame in cases:
            for _ in range(5):
                rich_frame.add(Spacer(20))
            table = Table([["Metric", "Details"], ["Revenue", rich_frame]]).column_widths([130, 130]).cell_padding(vertical=6, horizontal=6)
            table.node.resolved_width = 260
            table.node.resolved_height = table_height(table.node)

            with self.subTest(layout=rich_frame.node.content.get("layout", "flow")):
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

    def test_fixed_height_split_rejects_non_finite_height(self) -> None:
        spacer = Spacer(80)
        spacer.node.resolved_height = float("inf")

        with self.assertRaises(ValueError) as ctx:
            _split_flow_child(spacer.node, 40, 40)

        self.assertEqual(str(ctx.exception), "Fixed-height pagination requires finite heights")

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

    def test_flex_row_wrap_pagination_keeps_visual_rows_together(self) -> None:
        frame = Frame().flex("row", gap=4, wrap=True).padding(0).width(160)
        labels = [f"row-item-{index}" for index in range(6)]
        for label in labels:
            frame.add_text(label).width(68).font_size(8).line_height(10)
        resolve_widths(frame.node, 160)
        resolve_heights(frame.node, None)

        slices = split_frame_node(frame.node, 15, 15)
        slice_labels = [
            [str(child.content["text"]) for child in frame_slice.children if child.node_type == "text"]
            for frame_slice in slices
        ]

        self.assertEqual(slice_labels, [["row-item-0", "row-item-1"], ["row-item-2", "row-item-3"], ["row-item-4", "row-item-5"]])


    def test_flex_row_wrap_pagination_moves_first_row_to_following_page_when_it_fits(self) -> None:
        frame = Frame().flex("row", gap=4, wrap=True).padding(0).width(160)
        frame.add_text("first").width(68).font_size(8).line_height(10)
        frame.add_text("second").width(68).font_size(8).line_height(10)
        resolve_widths(frame.node, 160)
        resolve_heights(frame.node, None)

        slices = split_frame_node(frame.node, 5, 15)

        self.assertEqual(len(slices), 1)
        self.assertTrue(slices[0].content.get(STARTS_ON_FOLLOWING_PAGE))
        self.assertEqual([child.content["text"] for child in slices[0].children], ["first", "second"])

    def test_flex_row_wrap_pagination_preserves_row_gap_within_slice(self) -> None:
        frame = Frame().flex("row", wrap=True, row_gap=20, column_gap=4).padding(0).width(160)
        for index in range(4):
            frame.add_text(f"gap-item-{index}").width(68).font_size(8).line_height(10)
        resolve_widths(frame.node, 160)
        resolve_heights(frame.node, None)

        slices = split_frame_node(frame.node, 100, 100)

        self.assertEqual(len(slices), 1)
        self.assertEqual([child.local_y for child in slices[0].children], [0.0, 0.0, 30.0, 30.0])

    def test_flex_row_wrap_pagination_groups_justified_rows_by_wrap_rules(self) -> None:
        frame = Frame().flex("row", wrap=True, justify="center", gap=4).padding(0).width(160)
        for index in range(3):
            frame.add_text(f"center-item-{index}").width(68).font_size(8).line_height(10)
        resolve_widths(frame.node, 160)
        resolve_heights(frame.node, None)

        slices = split_frame_node(frame.node, 15, 15)
        slice_labels = [[str(child.content["text"]) for child in frame_slice.children] for frame_slice in slices]

        self.assertEqual(slice_labels, [["center-item-0", "center-item-1"], ["center-item-2"]])


    def test_flex_row_wrap_pagination_preserves_labels_without_duplicates(self) -> None:
        labels = [f"wrap-page-{index}" for index in range(18)]
        page = document().page((160, 90))
        frame = Frame().flex("row", gap=4, wrap=True).padding(4)
        for label in labels:
            frame.add_text(label).width(68).font_size(8).line_height(10)
        page.add(frame)

        resolve_widths(page.node, 160)
        resolve_heights(page.node, None)
        pages = paginate_page(page.node)

        extracted_labels = [
            str(text_node.content["text"])
            for page_slice in pages
            for frame_slice in page_slice.children
            for text_node in frame_slice.children
            if text_node.node_type == "text"
        ]

        self.assertGreater(len(pages), 1)
        self.assertCountEqual(extracted_labels, labels)
        self.assertEqual(len(extracted_labels), len(set(extracted_labels)))


class SubtotalRepeatTests(unittest.TestCase):
    def test_subtotal_repeat_true_repeats_in_paginated_slices(self) -> None:
        rows = [["Metric", "Value"]] + [[f"M{index}", str(index)] for index in range(12)]
        table = Table(rows).subtotal(["Total", "66"], repeat=True, background="#e2e8f0")
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 90, 90)

        self.assertGreater(len(slices), 1)
        self.assertTrue(all(table_rows(s)[-1][0] == "Total" for s in slices))

    def test_subtotal_repeat_false_does_not_repeat(self) -> None:
        rows = [["Metric", "Value"]] + [[f"M{index}", str(index)] for index in range(12)]
        table = Table(rows).subtotal(["Total", "66"], repeat=False)
        table.node.resolved_width = 200
        table.node.resolved_height = table_height(table.node)

        slices = _split_table_node(table.node, 90, 90)

        self.assertGreater(len(slices), 1)
        self.assertTrue(all(table_rows(s)[-1][0] != "Total" for s in slices[:-1]))
        self.assertEqual(table_rows(slices[-1])[-1][0], "Total")

    def test_subtotal_default_background_preserved(self) -> None:
        table = Table([["A", "1"], ["B", "2"]]).subtotal(["Total", "3"])

        self.assertEqual(
            table.node.content["footer_background"],
            parse_color("#f1f5f9"),
        )

    def test_subtotal_color_applied(self) -> None:
        table = Table([["A", "1"]]).subtotal(["Total", "1"], color="#1e293b")

        self.assertIsNotNone(table.node.content.get("footer_color"))

    def test_subtotal_chaining(self) -> None:
        table = Table([["A", "1"]])

        result = table.subtotal(["Total", "1"])

        self.assertIs(result, table)
        self.assertIsNotNone(table.node.content.get("footer_rows"))


class TextOverflowElementTests(unittest.TestCase):
    def test_text_overflow_api_accepts_table_like_modes(self) -> None:
        text = Text("alpha beta")

        self.assertIs(text.text_overflow("clip"), text)
        self.assertEqual(text.node.content["text_overflow"], "clip")
        self.assertIs(text.text_overflow("ellipsis"), text)
        self.assertEqual(text.node.content["text_overflow"], "ellipsis")
        self.assertIs(text.text_overflow("wrap"), text)
        self.assertEqual(text.node.content["text_overflow"], "wrap")
        with self.assertRaises(ValueError):
            text.text_overflow("fade")

    def test_text_ellipsis_paints_single_fitted_line_and_clips_box(self) -> None:
        text = Text("Alpha Beta Gamma").font("Helvetica").font_size(12).line_height(14).width(60).height(24).text_overflow("ellipsis").align("center").valign("middle")
        resolve_widths(text.node, 60)
        resolve_heights(text.node)
        item = RenderItem(text.node, Rect(10, 20, 60, 24), (), (0,))
        spy = _SpyAdapter()

        paint_text(cast(ReportLabCanvasAdapter, spy), item)

        self.assertEqual(spy.text_kwargs[0]["text_overflow"], "ellipsis")
        self.assertEqual(spy.text_kwargs[0]["text"], "Alpha B…")
        self.assertEqual(spy.text_kwargs[0]["height"], 24.0)
        self.assertEqual(spy.text_kwargs[0]["align"], "center")
        self.assertEqual(spy.text_kwargs[0]["valign"], "middle")
        self.assertEqual(spy.clip_rects, [Rect(10, 20, 60, 24)])

    def test_text_clip_collapses_newlines_and_preserves_link_rect(self) -> None:
        text = Text("Alpha\nBeta Gamma").font("Helvetica").font_size(12).line_height(14).width(90).height(20).text_overflow("clip").link("https://example.com")
        resolve_widths(text.node, 90)
        resolve_heights(text.node)
        item = RenderItem(text.node, Rect(0, 0, 90, 20), (), (0,))
        spy = _SpyAdapter()

        paint_text(cast(ReportLabCanvasAdapter, spy), item)

        self.assertEqual(spy.text_kwargs[0]["text"], "Alpha Beta Gamma")
        self.assertEqual(spy.text_kwargs[0]["text_overflow"], "clip")
        self.assertEqual(len(spy.links), 1)
        self.assertEqual(spy.links[0][0], "https://example.com")
        self.assertLessEqual(spy.links[0][1].width, 90)




class RichTextElementTests(unittest.TestCase):
    def test_rich_text_builder_stores_styled_runs_and_breaks(self) -> None:
        rich = RichText()
        result = rich.span("Revenue ").span("+18%", font="Helvetica", font_size=14, color="#166534", bold=True, italic=True, underline=True).br().span("renewals")

        self.assertIs(result, rich)
        self.assertEqual(rich.node.node_type, "rich_text")
        self.assertEqual(
            rich.node.content["runs"],
            [
                {"kind": "text", "text": "Revenue "},
                {"kind": "text", "text": "+18%", "font": "Helvetica", "font_size": 14.0, "color": "#166534", "bold": True, "italic": True, "underline": True},
                {"kind": "br"},
                {"kind": "text", "text": "renewals"},
            ],
        )

    def test_rich_text_clear_returns_self_and_allows_new_content(self) -> None:
        rich = RichText("Initial").span(" extra").br()

        result = rich.clear()

        self.assertIs(result, rich)
        self.assertEqual(rich.node.content["runs"], [])
        self.assertIs(rich.span("Replacement").br().text("Final"), rich)
        self.assertEqual(rich.node.content["runs"], [{"kind": "text", "text": "Final"}])

    def test_rich_text_layout_wraps_and_preserves_fragment_styles(self) -> None:
        rich = (
            RichText()
            .font_size(10)
            .line_height(12)
            .span("alpha beta gamma", color="#dc2626", underline=True)
            .span(" delta", font="Helvetica", font_size=14, bold=True, italic=True)
            .br()
            .span("tail")
        )

        lines = layout_rich_text(rich.node, 54)
        fragments = [fragment for line in lines for fragment in line.fragments]

        self.assertGreater(len(lines), 2)
        self.assertTrue(any(fragment.color == parse_color("#dc2626") for fragment in fragments))
        self.assertTrue(any(fragment.underline for fragment in fragments))
        self.assertIn("Helvetica-BoldOblique", {fragment.font_name for fragment in fragments})
        self.assertTrue(any(fragment.italic for fragment in fragments))
        self.assertEqual(lines[-1].fragments[0].text, "tail")

    def test_rich_text_painter_passes_fragment_styles_to_adapter(self) -> None:
        rich = (
            RichText()
            .font_size(10)
            .line_height(12)
            .span("A", font="Helvetica", color="#ff0000")
            .span("B", font="Courier", color="#0000ff")
            .width(100)
        )
        resolve_widths(rich.node, 100)
        resolve_heights(rich.node)
        item = RenderItem(rich.node, Rect(0, 0, 100, rich.node.resolved_height), (), (0,))
        spy = _SpyAdapter()

        paint_rich_text(cast(ReportLabCanvasAdapter, spy), item)

        self.assertEqual(spy.rich_text_fragments, ["A", "B"])
        self.assertEqual(spy.rich_text_fonts, ["Helvetica", "Courier"])
        self.assertEqual(spy.rich_text_colors, [parse_color("#ff0000"), parse_color("#0000ff")])

    def test_rich_text_italic_uses_registered_family_faces(self) -> None:
        font_dir = Path(__file__).resolve().parents[1] / "examples" / "fonts"
        register_font_family(
            "TestRichTextFamily",
            regular=font_dir / "NotoNaskhArabic-Medium.ttf",
            bold=font_dir / "NotoNaskhArabic-Bold.ttf",
            italic=font_dir / "NotoNaskhArabic-Medium.ttf",
            bold_italic=font_dir / "NotoNaskhArabic-Bold.ttf",
        )
        rich = RichText().span("italic", font_family="TestRichTextFamily", italic=True).span(" bold italic", font_family="TestRichTextFamily", bold=True, italic=True)

        fragments = [fragment for line in layout_rich_text(rich.node, 500) for fragment in line.fragments]

        self.assertEqual(fragments[0].font_name, "TestRichTextFamily-Italic")
        self.assertEqual(fragments[1].font_name, "TestRichTextFamily-BoldItalic")

    def test_rich_text_line_serialization_preserves_italic_and_underline(self) -> None:
        rich = RichText().span("alpha beta gamma", font="Helvetica", italic=True, underline=True).width(35)
        lines = layout_rich_text(rich.node, 35)

        runs = rich_text_runs_for_lines(lines)

        styled_runs = [run for run in runs if run.get("kind") == "text"]
        self.assertGreater(len(styled_runs), 1)
        self.assertTrue(all(run.get("italic") is True for run in styled_runs))
        self.assertTrue(all(run.get("underline") is True for run in styled_runs))


    def test_rich_text_letter_spacing_resolves_global_and_span_values(self) -> None:
        rich = RichText().font_size(10).letter_spacing("10%").span("AB").span("CD", font_size=20, letter_spacing="0.1em")

        lines = layout_rich_text(rich.node, 500)
        fragments = [fragment for line in lines for fragment in line.fragments]

        self.assertEqual([fragment.letter_spacing for fragment in fragments], [1.0, 2.0])
        self.assertEqual(lines[0].width, string_width("AB", "Helvetica", 10) + 1.0 + string_width("CD", "Helvetica", 20) + 2.0)

    def test_rich_text_spacing_affects_wrapping(self) -> None:
        compact = RichText().font("Helvetica").font_size(10).span("AB CD")
        spaced = RichText().font("Helvetica").font_size(10).letter_spacing(4).span("AB CD")

        compact_lines = layout_rich_text(compact.node, 31)
        spaced_lines = layout_rich_text(spaced.node, 31)

        self.assertEqual(len(compact_lines), 1)
        self.assertGreater(len(spaced_lines), 1)

    def test_reportlab_adapter_draw_rich_text_sets_fragment_char_spacing(self) -> None:
        rich = RichText().letter_spacing(1).span("A").span("B", letter_spacing=2)
        lines = layout_rich_text(rich.node, 100)
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_rich_text(10, 20, 100, lines)

        self.assertEqual(fake_canvas.text_object.char_spaces, [1.0, 2.0])

    def test_reportlab_adapter_draw_rich_text_uses_fragment_fonts_and_colors(self) -> None:
        rich = RichText().span("A", font="Helvetica", color="#ff0000").span("B", font="Courier", color="#0000ff")
        lines = layout_rich_text(rich.node, 100)
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_rich_text(10, 20, 100, lines)

        self.assertEqual(fake_canvas.text_object.output, ["A", "B"])
        self.assertEqual(fake_canvas.text_object.font_names, ["Helvetica", "Courier"])
        self.assertEqual(fake_canvas.text_object.fill_colors, [(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)])

    def test_reportlab_adapter_draw_rich_text_draws_underlined_fragments(self) -> None:
        rich = RichText().span("A", font="Helvetica", color="#ff0000", underline=True).span("B", font="Helvetica")
        lines = layout_rich_text(rich.node, 100)
        adapter = ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter)
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 200

        adapter.draw_rich_text(10, 20, 100, lines)

        self.assertEqual(len(fake_canvas.lines), 1)
        line = fake_canvas.lines[0]
        self.assertAlmostEqual(line[0], 10.0, places=3)
        self.assertAlmostEqual(line[2], 10.0 + string_width("A", "Helvetica", 12), places=3)
        self.assertEqual(fake_canvas.stroke_colors, [(1.0, 0.0, 0.0)])
        self.assertEqual(fake_canvas.stroke_alphas, [1.0])


class LayoutPrimitiveTests(unittest.TestCase):
    def test_layout_api_rejects_unbounded_track_counts_and_nonfinite_gap(self) -> None:
        with self.assertRaises(ValueError):
            _ = Frame().columns(65)
        with self.assertRaises(ValueError):
            _ = Frame().grid(65)
        with self.assertRaises(ValueError):
            _ = Frame().gap(float("inf"))

    def test_flex_row_wrap_api_is_accepted_and_stored(self) -> None:
        frame = Frame().flex("row", wrap=True)

        self.assertEqual(frame.node.content["layout"], "flex")
        self.assertEqual(frame.node.content["flex_direction"], "row")
        self.assertIs(frame.node.content["flex_wrap"], True)

    def test_flex_column_wrap_api_remains_rejected(self) -> None:
        with self.assertRaises(ValueError) as error:
            _ = Frame().flex("column", wrap=True)

        self.assertEqual(str(error.exception), "flex wrap is only supported for row direction")

    def test_flex_wrap_state_is_cleared_when_switching_to_column(self) -> None:
        frame = Frame().flex("row", wrap=True).flex("column")

        self.assertFalse(frame.node.content.get("flex_wrap", False))

    def test_flex_row_without_wrap_keeps_equal_split_widths(self) -> None:
        frame = Frame().flex("row", gap=10).width(210)
        first = frame.add_spacer(10)
        second = frame.add_spacer(10)

        resolve_widths(frame.node, 210)

        self.assertEqual(first.node.resolved_width, 100)
        self.assertEqual(second.node.resolved_width, 100)

    def test_flex_row_wrap_pass2_preserves_fixed_child_width(self) -> None:
        frame = Frame().flex("row", wrap=True).width(200)
        fixed = frame.add_spacer(10).width(80)
        another = frame.add_spacer(10).width(50)

        resolve_widths(frame.node, 200)

        self.assertEqual(fixed.node.resolved_width, 80)
        self.assertEqual(another.node.resolved_width, 50)

    def test_flex_row_wrap_pass2_resolves_percent_child_width_against_content_box(self) -> None:
        frame = Frame().flex("row", wrap=True).width(240).padding(horizontal=20)
        percent = frame.add_spacer(10).width("50%")

        resolve_widths(frame.node, 240)

        self.assertEqual(percent.node.resolved_width, 100)

    def test_flex_row_wrap_pass2_uses_text_natural_width_for_auto_text(self) -> None:
        text_value = "natural width"
        frame = Frame().flex("row", wrap=True).width(300)
        text = frame.add_text(text_value).font("Helvetica").font_size(12).line_height(14)

        resolve_widths(frame.node, 300)

        expected_width = string_width(text_value, "Helvetica", 12)
        self.assertGreater(text.node.resolved_width, 0)
        self.assertLess(text.node.resolved_width, 300)
        self.assertAlmostEqual(text.node.resolved_width, expected_width, places=3)

    def test_flex_row_wrap_pass2_falls_back_to_parent_width_for_complex_auto_child(self) -> None:
        frame = Frame().flex("row", wrap=True).width(180).padding(horizontal=15)
        complex_child = Frame().padding(4)
        complex_child.add_text("nested")
        frame.add(complex_child)

        resolve_widths(frame.node, 180)

        self.assertEqual(complex_child.node.resolved_width, 150)

    def test_flex_row_wrap_positions_fixed_children_across_rows(self) -> None:
        frame = Frame().flex("row", gap=10, wrap=True).width(120)
        children = [frame.add_spacer(20).width(width) for width in (70, 40, 50)]
        frame.node.resolved_width = 120
        for child, width in zip(children, (70, 40, 50)):
            child.node.resolved_width = width
            child.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((children[0].node.local_x, children[0].node.local_y), (0, 0))
        self.assertEqual((children[1].node.local_x, children[1].node.local_y), (80, 0))
        self.assertEqual((children[2].node.local_x, children[2].node.local_y), (0, 30))
        self.assertEqual(frame.node.resolved_height, 50)

    def test_flex_row_wrap_uses_gap_horizontally_and_between_rows(self) -> None:
        frame = Frame().flex("row", gap=8, wrap=True).width(100)
        children = [frame.add_spacer(12).width(width) for width in (40, 40, 40)]
        frame.node.resolved_width = 100
        for child in children:
            child.node.resolved_width = 40
            child.node.resolved_height = 12

        resolve_heights(frame.node, None)

        self.assertEqual(children[1].node.local_x, 48)
        self.assertEqual(children[2].node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 32)

    def test_flex_row_wrap_respects_parent_padding_boundary(self) -> None:
        frame = Frame().flex("row", gap=10, wrap=True).width(140).padding(top=5, right=10, bottom=7, left=10)
        first = frame.add_spacer(20).width(70)
        second = frame.add_spacer(20).width(60)
        frame.node.resolved_width = 140
        for child, width in ((first, 70), (second, 60)):
            child.node.resolved_width = width
            child.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((first.node.local_x, first.node.local_y), (10, 5))
        self.assertEqual((second.node.local_x, second.node.local_y), (10, 35))
        self.assertEqual(frame.node.resolved_height, 62)

    def test_flex_row_wrap_accounts_for_margins_when_wrapping_and_positioning(self) -> None:
        frame = Frame().flex("row", gap=10, wrap=True).width(120)
        first = frame.add_spacer(20).width(50).margin(right=10)
        second = frame.add_spacer(20).width(50).margin(top=3, left=5)
        frame.node.resolved_width = 120
        for child in (first, second):
            child.node.resolved_width = 50
            child.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((first.node.local_x, first.node.local_y), (0, 0))
        self.assertEqual((second.node.local_x, second.node.local_y), (5, 33))
        self.assertEqual(frame.node.resolved_height, 53)

    def test_flex_row_wrap_places_oversized_child_alone(self) -> None:
        frame = Frame().flex("row", gap=10, wrap=True).width(100)
        oversized = frame.add_spacer(20).width(140)
        following = frame.add_spacer(20).width(40)
        frame.node.resolved_width = 100
        oversized.node.resolved_width = 140
        oversized.node.resolved_height = 20
        following.node.resolved_width = 40
        following.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((oversized.node.local_x, oversized.node.local_y), (0, 0))
        self.assertEqual((following.node.local_x, following.node.local_y), (0, 30))
        self.assertEqual(frame.node.resolved_height, 50)

    def test_flex_row_wrap_uses_tallest_item_for_row_height(self) -> None:
        frame = Frame().flex("row", gap=10, wrap=True).width(110)
        children = [frame.add_spacer(height).width(width) for width, height in ((50, 20), (50, 40), (100, 10))]
        frame.node.resolved_width = 110
        for child, width, height in zip(children, (50, 50, 100), (20, 40, 10)):
            child.node.resolved_width = width
            child.node.resolved_height = height

        resolve_heights(frame.node, None)

        self.assertEqual((children[0].node.local_y, children[1].node.local_y), (0, 0))
        self.assertEqual(children[2].node.local_y, 50)
        self.assertEqual(frame.node.resolved_height, 60)

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

    # --- v2.9 Flex Refinements TDD Tests ---

    # -- API storage --

    def test_flex_row_justify_align_row_gap_column_gap_api_is_accepted_and_stored(self) -> None:
        frame = Frame().flex("row", justify="center", align="end", row_gap=6, column_gap=12)

        self.assertEqual(frame.node.content["flex_justify"], "center")
        self.assertEqual(frame.node.content["flex_align"], "end")
        self.assertEqual(frame.node.content["row_gap"], 6.0)
        self.assertEqual(frame.node.content["column_gap"], 12.0)

    def test_flex_column_justify_align_row_gap_api_is_accepted_and_stored(self) -> None:
        frame = Frame().flex("column", justify="end", align="center", row_gap=10)

        self.assertEqual(frame.node.content["flex_justify"], "end")
        self.assertEqual(frame.node.content["flex_align"], "center")
        self.assertEqual(frame.node.content["row_gap"], 10.0)

    # -- Invalid API values --

    def test_flex_invalid_justify_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as error:
            _ = Frame().flex("row", justify="diagonal")

        self.assertEqual(str(error.exception), "Unsupported flex justify: diagonal")

    def test_flex_invalid_align_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as error:
            _ = Frame().flex("row", align="baseline")

        self.assertEqual(str(error.exception), "Unsupported flex align: baseline")

    # -- Default backward compatibility --

    def test_flex_row_gap_only_backward_compatibility(self) -> None:
        """Existing gap=10 row layout must produce identical positions to v2.8."""
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

    def test_flex_column_gap_only_backward_compatibility(self) -> None:
        """Existing gap=10 column layout must produce identical positions to v2.8."""
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

    def test_flex_row_wrap_gap_only_backward_compatibility(self) -> None:
        """Existing gap=10 wrap layout must produce identical positions to v2.8."""
        frame = Frame().flex("row", gap=10, wrap=True).width(120)
        children = [frame.add_spacer(20).width(width) for width in (70, 40, 50)]
        frame.node.resolved_width = 120
        for child, width in zip(children, (70, 40, 50)):
            child.node.resolved_width = width
            child.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((children[0].node.local_x, children[0].node.local_y), (0, 0))
        self.assertEqual((children[1].node.local_x, children[1].node.local_y), (80, 0))
        self.assertEqual((children[2].node.local_x, children[2].node.local_y), (0, 30))
        self.assertEqual(frame.node.resolved_height, 50)

    # -- Row justify positions --

    def test_flex_row_justify_center_positions_children(self) -> None:
        frame = Frame().flex("row", gap=10, justify="center").width(300)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        for child in (first, second):
            child.node.resolved_width = 100
            child.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_x, 45)
        self.assertEqual(second.node.local_x, 155)

    def test_flex_row_justify_end_positions_children(self) -> None:
        frame = Frame().flex("row", gap=10, justify="end").width(300)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        for child in (first, second):
            child.node.resolved_width = 100
            child.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_x, 90)
        self.assertEqual(second.node.local_x, 200)

    def test_flex_row_justify_space_between_positions_children(self) -> None:
        frame = Frame().flex("row", gap=10, justify="space-between").width(300)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(20).width(100)
        third = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        for child in (first, second, third):
            child.node.resolved_width = 100
            child.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_x, 0)
        self.assertEqual(second.node.local_x, 110)
        self.assertEqual(third.node.local_x, 220)

    def test_flex_row_justify_space_between_single_child_behaves_as_start(self) -> None:
        frame = Frame().flex("row", gap=10, justify="space-between").width(300)
        only = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        only.node.resolved_width = 100
        only.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(only.node.local_x, 0)

    def test_flex_row_justify_negative_remaining_space_clamps_to_zero(self) -> None:
        """When children overflow content width, remaining space clamps to 0."""
        frame = Frame().flex("row", gap=10, justify="center").width(200)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(20).width(100)
        third = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 200
        for child in (first, second, third):
            child.node.resolved_width = 100
            child.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_x, 0)
        self.assertEqual(second.node.local_x, 110)
        self.assertEqual(third.node.local_x, 220)

    # -- Row align positions --

    def test_flex_row_align_center_positions_shorter_child(self) -> None:
        frame = Frame().flex("row", gap=10, align="center").width(300)
        tall = frame.add_spacer(60).width(100)
        short = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        tall.node.resolved_width = 100
        tall.node.resolved_height = 60
        short.node.resolved_width = 100
        short.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(tall.node.local_x, 0)
        self.assertEqual(short.node.local_x, 110)
        self.assertEqual(tall.node.local_y, 0)
        self.assertEqual(short.node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 60)

    def test_flex_row_align_end_positions_shorter_child(self) -> None:
        frame = Frame().flex("row", gap=10, align="end").width(300)
        tall = frame.add_spacer(60).width(100)
        short = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        tall.node.resolved_width = 100
        tall.node.resolved_height = 60
        short.node.resolved_width = 100
        short.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(tall.node.local_x, 0)
        self.assertEqual(short.node.local_x, 110)
        self.assertEqual(tall.node.local_y, 0)
        self.assertEqual(short.node.local_y, 40)
        self.assertEqual(frame.node.resolved_height, 60)

    # -- Wrapped row: column_gap and row_gap separation --

    def test_flex_row_wrap_column_gap_controls_horizontal_spacing(self) -> None:
        frame = Frame().flex("row", wrap=True, column_gap=12, row_gap=10).width(100)
        children = [frame.add_spacer(12).width(width) for width in (40, 40, 40)]
        frame.node.resolved_width = 100
        for child in children:
            child.node.resolved_width = 40
            child.node.resolved_height = 12

        resolve_heights(frame.node, None)

        self.assertEqual(children[1].node.local_x, 52)
        self.assertEqual(children[2].node.local_y, 22)
        self.assertEqual(frame.node.resolved_height, 34)

    def test_flex_row_wrap_row_gap_controls_vertical_spacing(self) -> None:
        frame = Frame().flex("row", wrap=True, column_gap=12, row_gap=10).width(100)
        children = [frame.add_spacer(12).width(40) for _ in range(3)]
        frame.node.resolved_width = 100
        for child in children:
            child.node.resolved_width = 40
            child.node.resolved_height = 12

        resolve_heights(frame.node, None)

        self.assertEqual(children[1].node.local_y, 0)
        self.assertEqual(children[2].node.local_y, 22)
        self.assertEqual(frame.node.resolved_height, 34)

    # -- Wrapped row per-row justify and align --

    def test_flex_row_wrap_justify_center_applies_per_row(self) -> None:
        frame = Frame().flex("row", wrap=True, gap=10, justify="center").width(200)
        a = frame.add_spacer(20).width(80)
        b = frame.add_spacer(20).width(80)
        c = frame.add_spacer(20).width(80)
        frame.node.resolved_width = 200
        for child in (a, b, c):
            child.node.resolved_height = 20
            child.node.resolved_width = 80

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        # Row 1: a(80) + gap(10) + b(80) = 170, remaining=30, center offset=15
        self.assertEqual(a.node.local_x, 15)
        self.assertEqual(b.node.local_x, 105)
        # Row 2: c(80) alone, remaining=120, center offset=60
        self.assertEqual(c.node.local_x, 60)
        self.assertEqual(c.node.local_y, 30)

    def test_flex_row_wrap_align_end_applies_per_row(self) -> None:
        frame = Frame().flex("row", wrap=True, gap=10, align="end").width(140)
        a = frame.add_spacer(40).width(60)
        b = frame.add_spacer(20).width(60)
        c = frame.add_spacer(30).width(60)
        frame.node.resolved_width = 140
        for child, height in ((a, 40), (b, 20), (c, 30)):
            child.node.resolved_width = 60
            child.node.resolved_height = height

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(a.node.local_x, 0)
        self.assertEqual(b.node.local_x, 70)
        self.assertEqual(a.node.local_y, 0)
        self.assertEqual(b.node.local_y, 20)
        self.assertEqual(c.node.local_y, 50)

    def test_flex_row_wrap_oversized_child_remains_alone(self) -> None:
        """Oversized single child placed alone, may overflow, does not stretch or shrink."""
        frame = Frame().flex("row", wrap=True, gap=10, justify="center").width(100)
        oversized = frame.add_spacer(20).width(140)
        following = frame.add_spacer(20).width(40)
        frame.node.resolved_width = 100
        oversized.node.resolved_width = 140
        oversized.node.resolved_height = 20
        following.node.resolved_width = 40
        following.node.resolved_height = 20

        resolve_heights(frame.node, None)

        self.assertEqual((oversized.node.local_x, oversized.node.local_y), (0, 0))
        self.assertEqual((following.node.local_x, following.node.local_y), (30, 30))
        self.assertEqual(frame.node.resolved_height, 50)

    # -- Column: row_gap vertical stacking, column_gap ignored --

    def test_flex_column_row_gap_controls_vertical_spacing(self) -> None:
        frame = Frame().flex("column", row_gap=15).width(120)
        first = Spacer(20)
        second = Spacer(30)
        frame.add(first).add(second)
        frame.node.resolved_width = 120
        first.node.resolved_width = 120
        first.node.resolved_height = 20
        second.node.resolved_width = 120
        second.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual((first.node.local_x, first.node.local_y), (0, 0))
        self.assertEqual((second.node.local_x, second.node.local_y), (0, 35))
        self.assertEqual(frame.node.resolved_height, 65)

    def test_flex_column_column_gap_ignored_for_stacking(self) -> None:
        frame = Frame().flex("column", column_gap=50).width(120)
        first = Spacer(20)
        second = Spacer(30)
        frame.add(first).add(second)
        frame.node.resolved_width = 120
        first.node.resolved_width = 120
        first.node.resolved_height = 20
        second.node.resolved_width = 120
        second.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(first.node.local_y, 0)
        self.assertEqual(second.node.local_y, 20)
        self.assertEqual(frame.node.resolved_height, 50)

    def test_flex_column_align_center_x_position(self) -> None:
        frame = Frame().flex("column", gap=10, align="center").width(300)
        wide = frame.add_spacer(20).width(200)
        narrow = frame.add_spacer(30).width(100)
        frame.node.resolved_width = 300
        wide.node.resolved_width = 200
        wide.node.resolved_height = 20
        narrow.node.resolved_width = 100
        narrow.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(wide.node.local_x, 50)
        self.assertEqual(narrow.node.local_x, 100)
        self.assertEqual(frame.node.resolved_height, 60)

    def test_flex_column_align_end_x_position(self) -> None:
        frame = Frame().flex("column", gap=10, align="end").width(300)
        wide = frame.add_spacer(20).width(200)
        narrow = frame.add_spacer(30).width(100)
        frame.node.resolved_width = 300
        wide.node.resolved_width = 200
        wide.node.resolved_height = 20
        narrow.node.resolved_width = 100
        narrow.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, None)

        self.assertEqual(wide.node.local_x, 100)
        self.assertEqual(narrow.node.local_x, 200)
        self.assertEqual(frame.node.resolved_height, 60)

    # -- Column: explicit-height justify --

    def test_flex_column_justify_center_with_explicit_height(self) -> None:
        frame = Frame().flex("column", gap=10, justify="center").width(300).height(100)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(30).width(100)
        frame.node.resolved_width = 300
        first.node.resolved_width = 100
        first.node.resolved_height = 20
        second.node.resolved_width = 100
        second.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, 100)

        self.assertEqual(first.node.local_y, 20)
        self.assertEqual(second.node.local_y, 50)

    def test_flex_column_justify_end_with_explicit_height(self) -> None:
        frame = Frame().flex("column", gap=10, justify="end").width(300).height(100)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(30).width(100)
        frame.node.resolved_width = 300
        first.node.resolved_width = 100
        first.node.resolved_height = 20
        second.node.resolved_width = 100
        second.node.resolved_height = 30

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, 100)

        self.assertEqual(first.node.local_y, 40)
        self.assertEqual(second.node.local_y, 70)

    def test_flex_column_justify_space_between_with_explicit_height(self) -> None:
        frame = Frame().flex("column", gap=10, justify="space-between").width(300).height(120)
        first = frame.add_spacer(20).width(100)
        second = frame.add_spacer(20).width(100)
        third = frame.add_spacer(20).width(100)
        frame.node.resolved_width = 300
        for child in (first, second, third):
            child.node.resolved_width = 100
            child.node.resolved_height = 20

        from smart_report.layout.pass3_heights import _layout_container
        _layout_container(frame.node, 120)

        self.assertEqual(first.node.local_y, 0)
        self.assertEqual(second.node.local_y, 50)
        self.assertEqual(third.node.local_y, 100)

    def test_flex_column_justify_noop_when_auto_height(self) -> None:
        """Justify has no visible effect when parent height is auto."""
        frame = Frame().flex("column", gap=10, justify="center").width(120)
        first = Spacer(20)
        second = Spacer(30)
        frame.add(first).add(second)
        frame.node.resolved_width = 120
        first.node.resolved_width = 120
        first.node.resolved_height = 20
        second.node.resolved_width = 120
        second.node.resolved_height = 30

        resolve_heights(frame.node, None)

        self.assertEqual(first.node.local_y, 0)
        self.assertEqual(second.node.local_y, 30)
        self.assertEqual(frame.node.resolved_height, 60)



@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class TableV2PdfTests(unittest.TestCase):
    def test_flex_row_wrap_pdf_labels_are_extractable(self) -> None:
        assert PdfReader is not None
        labels = [f"pdf-wrap-{index}" for index in range(8)]

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "flex_wrap_labels.pdf"
            doc = document()
            page = doc.page((180, 180))
            frame = Frame().flex("row", gap=4, wrap=True).padding(12)
            for label in labels:
                frame.add_text(label).width(70).font_size(8).line_height(10)
            page.add(frame)
            doc.save(str(output))

            extracted_text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)

        for label in labels:
            self.assertIn(label, extracted_text)

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

    def test_linked_rich_text_table_cell_emits_url_annotation(self) -> None:
        assert PdfReader is not None
        rich_text = Text("Open report details").font_size(10).line_height(12).link("https://example.com/table-rich")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "rich_text_table_link.pdf"
            doc = document()
            page = doc.page("A4")
            frame = Frame().padding(36)
            frame.add(Table([["Metric", "Details"], ["Revenue", rich_text]]).column_widths([100, 180]).cell_padding(vertical=6, horizontal=8).font_size(10).line_height(12))
            page.add(frame)
            doc.save(str(output))

            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertEqual(page_uris, [["https://example.com/table-rich"]])

    def test_plain_string_table_cells_emit_no_url_annotations(self) -> None:
        assert PdfReader is not None

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "plain_table_no_link.pdf"
            doc = document()
            page = doc.page("A4")
            frame = Frame().padding(36)
            frame.add(Table([["Metric", "Details"], ["Revenue", "Open report details"]]).column_widths([100, 180]).cell_padding(vertical=6, horizontal=8).font_size(10).line_height(12))
            page.add(frame)
            doc.save(str(output))

            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertEqual(page_uris, [[]])

    def test_paginated_linked_rich_text_table_cell_keeps_url_annotations(self) -> None:
        assert PdfReader is not None
        rich_text = Text(" ".join(f"linked-note-{index}" for index in range(1200))).font_size(10).line_height(12).link("https://example.com/table-paginated")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "paginated_rich_text_table_link.pdf"
            doc = document()
            page = doc.page("A4")
            frame = Frame().padding(36)
            frame.add(Table([["Metric", "Details"], ["Revenue", rich_text]]).column_widths([100, 160]).cell_padding(vertical=6, horizontal=6).font_size(10).line_height(12))
            page.add(frame)
            doc.save(str(output))

            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertGreater(len(page_uris), 1)
        self.assertTrue(all(uris for uris in page_uris))
        self.assertTrue(all(uri == "https://example.com/table-paginated" for uris in page_uris for uri in uris))

@contextmanager
def _patched_table_string_width(string_width: object) -> Iterator[None]:
    original = table_model_module.registry_string_width
    table_model_module.registry_string_width = string_width  # type: ignore[assignment]
    try:
        yield
    finally:
        table_model_module.registry_string_width = original


class _SpyAdapter:
    def __init__(self) -> None:
        self.rounded_clips: list[tuple[float, float, float, float, CornerRadii]] = []
        self.clip_rects: list[Rect] = []
        self.links: list[tuple[str, Rect]] = []
        self.drawn_radii: list[CornerRadii] = []
        self.rect_fills: list[object] = []
        self.images: list[tuple[Rect, str]] = []
        self.image_radii: list[CornerRadii | None] = []
        self.line_widths: list[float] = []
        self.line_colors: list[object] = []
        self.lines: list[tuple[float, float, float, float, float]] = []
        self.texts: list[str] = []
        self.text_kwargs: list[dict[str, object]] = []
        self.rects: list[Rect] = []
        self.rich_text_fragments: list[str] = []
        self.rich_text_fonts: list[str] = []
        self.rich_text_colors: list[object] = []
        self.rich_text_italics: list[bool] = []
        self.rich_text_underlines: list[bool] = []

    @contextmanager
    def isolated_state(self) -> Iterator["_SpyAdapter"]:
        yield self

    def apply_clip_rounded_rect(self, rect: Rect, radius: CornerRadii) -> None:
        self.rounded_clips.append((rect.x, rect.y, rect.width, rect.height, radius))

    def apply_clip_rect(self, rect: Rect) -> None:
        self.clip_rects.append(rect)

    def draw_rect(self, rect: Rect, fill: object = None, stroke: object = None, stroke_width: float = 0.0, radius: CornerRadii | None = None) -> None:
        _ = (rect, fill, stroke, stroke_width)
        self.rects.append(rect)
        self.rect_fills.append(fill)
        self.drawn_radii.append(radius or CornerRadii())

    def draw_text(self, **kwargs: object) -> None:
        self.text_kwargs.append(dict(kwargs))
        self.texts.append(str(kwargs.get("text", "")))

    def draw_rich_text(self, **kwargs: object) -> None:
        lines = kwargs.get("lines")
        if not isinstance(lines, list):
            return
        for line in lines:
            for fragment in getattr(line, "fragments", ()):
                self.rich_text_fragments.append(str(getattr(fragment, "text", "")))
                self.rich_text_fonts.append(str(getattr(fragment, "font_name", "")))
                self.rich_text_colors.append(getattr(fragment, "color", None))
                self.rich_text_italics.append(bool(getattr(fragment, "italic", False)))
                self.rich_text_underlines.append(bool(getattr(fragment, "underline", False)))

    def draw_line(self, x1: float, y1: float, x2: float, y2: float, color: object, stroke_width: float) -> None:
        self.line_widths.append(float(stroke_width))
        self.line_colors.append(color)
        self.lines.append((float(x1), float(y1), float(x2), float(y2), float(stroke_width)))

    def draw_image(self, _source: object, rect: Rect, opacity: float = 1.0, fit: str = "stretch", radius: CornerRadii | None = None) -> None:
        _ = opacity
        self.images.append((rect, fit))
        self.image_radii.append(radius)

    def link_url(self, url: str, rect: Rect) -> None:
        self.links.append((url, rect))


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
        self.char_spaces: list[float] = []

    def setFont(self, _font_name: str, _font_size: float, _leading: float | None = None) -> None:
        _ = (_font_size, _leading)
        self.font_names.append(_font_name)

    def setFillColorRGB(self, red: float, green: float, blue: float) -> None:
        self.fill_colors.append((red, green, blue))

    def setTextOrigin(self, _x: float, _y: float) -> None:
        self.origins.append((_x, _y))

    def setLeading(self, _leading: float) -> None:
        return

    def setCharSpace(self, char_space: float) -> None:
        self.char_spaces.append(char_space)

    def textOut(self, _text: str) -> None:
        self.output.append(_text)

    def textLine(self, _text: str = "") -> None:
        return


class _FakePath:
    def __init__(self) -> None:
        self.commands: list[tuple[object, ...]] = []

    def rect(self, x: float, y: float, width: float, height: float) -> None:
        self.commands.append(("rect", x, y, width, height))

    def roundRect(self, x: float, y: float, width: float, height: float, radius: float) -> None:
        self.commands.append(("roundRect", x, y, width, height, radius))

    def moveTo(self, x: float, y: float) -> None:
        self.commands.append(("moveTo", x, y))

    def lineTo(self, x: float, y: float) -> None:
        self.commands.append(("lineTo", x, y))

    def curveTo(self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        self.commands.append(("curveTo", x1, y1, x2, y2, x3, y3))

    def close(self) -> None:
        self.commands.append(("close",))


class _FakeCanvas:
    def __init__(self) -> None:
        self.text_object = _FakeTextObject()
        self.fill_alphas: list[float] = []
        self.round_rects: list[tuple[float, float, float, float, float, int, int]] = []
        self.drawn_paths: list[list[tuple[object, ...]]] = []
        self.draw_image_rects: list[tuple[float, float, float, float]] = []
        self.lines: list[tuple[float, float, float, float]] = []
        self.stroke_colors: list[tuple[float, float, float]] = []
        self.stroke_alphas: list[float] = []
        self.line_widths: list[float] = []

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
        self.stroke_colors.append((r, g, b))

    def setFillAlpha(self, alpha: float) -> None:
        self.fill_alphas.append(alpha)

    def setStrokeAlpha(self, alpha: float) -> None:
        self.stroke_alphas.append(alpha)

    def setLineWidth(self, width: float) -> None:
        self.line_widths.append(width)

    def rect(self, x: float, y: float, width: float, height: float, stroke: int = 1, fill: int = 0) -> None:
        _ = (x, y, width, height, stroke, fill)

    def roundRect(self, x: float, y: float, width: float, height: float, radius: float, stroke: int = 1, fill: int = 0) -> None:
        self.round_rects.append((x, y, width, height, radius, stroke, fill))

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.lines.append((x1, y1, x2, y2))

    def drawPath(self, path: object, stroke: int = 1, fill: int = 0) -> None:
        _ = (stroke, fill)
        if isinstance(path, _FakePath):
            self.drawn_paths.append(path.commands)

    def beginPath(self) -> _FakePath:
        return _FakePath()

    def clipPath(self, path: object, stroke: int = 0, fill: int = 0) -> None:
        _ = (stroke, fill)
        if isinstance(path, _FakePath):
            self.drawn_paths.append(path.commands)

    def setFont(self, font_name: str, font_size: float, leading: float | None = None) -> None:
        _ = (font_name, font_size, leading)
        return

    def drawImage(self, image: object, x: float, y: float, width: float, height: float, mask: object | None = None) -> None:
        _ = (image, mask)
        self.draw_image_rects.append((x, y, width, height))

    def translate(self, dx: float, dy: float) -> None:
        _ = (dx, dy)
        return

    def scale(self, x: float, y: float) -> None:
        _ = (x, y)
        return

    def setPageSize(self, size: tuple[float, float]) -> None:
        _ = size
        return

    def setTitle(self, value: str) -> None:
        _ = value
        return

    def setAuthor(self, value: str) -> None:
        _ = value
        return

    def setSubject(self, value: str) -> None:
        _ = value
        return

    def setKeywords(self, value: str) -> None:
        _ = value
        return

    def bookmarkPage(self, key: str) -> None:
        _ = key
        return

    def addOutlineEntry(self, title: str, key: str, level: int = 0, closed: bool = False) -> None:
        _ = (title, key, level, closed)
        return

    def showPage(self) -> None:
        return

    def save(self) -> None:
        return

    def linkURL(self, url: str, rect: object, relative: int = 0, thickness: int = 0) -> None:
        _ = (url, rect, relative, thickness)
        return


if __name__ == "__main__":
    unittest.main()
