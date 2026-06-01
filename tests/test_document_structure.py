"""Regression tests for planned v2.4 document structure APIs."""

from __future__ import annotations

from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from smart_report import Canvas, Frame, Text, document
from smart_report.layout.node import LayoutNode, PositionMode, Rect, Style
from smart_report.layout.pass2_widths import resolve_widths
from smart_report.layout.pass3_heights import resolve_heights
from smart_report.layout.pass4_render import build_render_list
from smart_report.layout.text_wrap import wrap_text
from smart_report.render.rl_adapter import ReportLabCanvasAdapter

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def _save_temp_pdf(doc: object, name: str = "document_structure.pdf") -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp_dir = tempfile.TemporaryDirectory()
    output = Path(temp_dir.name) / name
    save = getattr(doc, "save")
    save(str(output))
    return temp_dir, output


def _page_texts(reader: Any) -> list[str]:
    return [(page.extract_text() or "") for page in reader.pages]


def _document_text(reader: Any) -> str:
    return "\n".join(_page_texts(reader))


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


def _outline_titles(reader: Any) -> list[str]:
    titles: list[str] = []

    def collect(items: object) -> None:
        if isinstance(items, list):
            for item in items:
                collect(item)
            return
        title = getattr(items, "title", None)
        if isinstance(title, str):
            titles.append(title)

    collect(getattr(reader, "outline", []))
    return titles


def _metadata_value(reader: Any, key: str) -> str:
    metadata = reader.metadata
    value = getattr(metadata, key, None)
    if value is None and isinstance(metadata, dict):
        value = metadata.get(key) or metadata.get(f"/{key.lstrip('/')}")
    return "" if value is None else str(value)


def _fill_section_page(page: object, prefix: str, count: int = 4) -> None:
    frame = Frame().padding(36)
    for index in range(count):
        frame.add_text(f"{prefix} body line {index + 1}").font_size(12).line_height(16)
    add = getattr(page, "add")
    add(frame)


def _render_node(
    node_type: str,
    name: str,
    *,
    z_index: int = 0,
    absolute: bool = False,
    children: list[LayoutNode] | None = None,
) -> LayoutNode:
    style = Style(z_index=z_index)
    if absolute:
        style.position = PositionMode.ABSOLUTE
    node = LayoutNode(
        node_type=node_type,
        style=style,
        name=name,
        resolved_width=100.0,
        resolved_height=40.0,
    )
    for child in children or []:
        _ = node.add_child(child)
    return node


def _rendered_names(root: LayoutNode) -> list[str]:
    return [item.node.name or item.node.node_type for item in build_render_list(root)]


def _painted_names_by_page_from_save_to_bytes(doc: object) -> list[list[str]]:
    from smart_report.render import painters

    records: list[tuple[int, str]] = []
    painters_module = cast(Any, painters)
    original_paint = painters_module.paint_render_item

    def record_paint(adapter: Any, item: Any) -> None:
        page_index = item.node.page_index
        records.append((0 if page_index is None else int(page_index), item.node.name or item.node.node_type))
        original_paint(adapter, item)

    painters_module.paint_render_item = record_paint
    try:
        save_to_bytes = getattr(doc, "save_to_bytes")
        _ = save_to_bytes()
    finally:
        painters_module.paint_render_item = original_paint

    names_by_page: list[list[str]] = []
    for page_index, name in records:
        while len(names_by_page) <= page_index:
            names_by_page.append([])
        names_by_page[page_index].append(name)
    return names_by_page


def _resolve_page_layout(page: Any) -> LayoutNode:
    node = cast(LayoutNode, page.node)
    resolve_widths(node)
    resolve_heights(node)
    return node


def _child_by_name(node: LayoutNode, name: str) -> LayoutNode:
    for child in node.children:
        if child.name == name:
            return child
    raise AssertionError(f"Missing child named {name!r}")


class RenderOrderPass4Tests(unittest.TestCase):
    def test_container_background_renders_before_children(self) -> None:
        panel = _render_node(
            "canvas",
            "panel-background",
            z_index=5,
            children=[_render_node("text", "panel-label", z_index=-1)],
        )
        page = _render_node("page", "page", children=[panel])

        self.assertEqual(_rendered_names(page), ["panel-background", "panel-label"])

    def test_higher_z_index_paints_after_lower_z_index_inside_canvas(self) -> None:
        chart = _render_node(
            "canvas",
            "chart-background",
            children=[
                _render_node("rect", "forecast-band", z_index=4),
                _render_node("line", "baseline", z_index=-2),
            ],
        )
        page = _render_node("page", "page", children=[chart])

        self.assertEqual(_rendered_names(page), ["chart-background", "baseline", "forecast-band"])

    def test_equal_z_index_preserves_tree_order(self) -> None:
        canvas = _render_node(
            "canvas",
            "canvas-background",
            children=[
                _render_node("text", "first-label", z_index=2),
                _render_node("text", "second-label", z_index=2),
            ],
        )
        page = _render_node("page", "page", children=[canvas])

        self.assertEqual(_rendered_names(page), ["canvas-background", "first-label", "second-label"])

    def test_page_absolute_layers_and_canvas_children_compose_predictably(self) -> None:
        page = _render_node(
            "page",
            "page",
            children=[
                _render_node("rect", "page-underlay", z_index=-10, absolute=True),
                _render_node(
                    "canvas",
                    "chart-background",
                    children=[_render_node("line", "chart-highlight", z_index=10)],
                ),
                _render_node("text", "page-annotation", absolute=True),
                _render_node("rect", "page-overlay", z_index=10, absolute=True),
            ],
        )

        self.assertEqual(
            _rendered_names(page),
            ["page-underlay", "chart-background", "chart-highlight", "page-annotation", "page-overlay"],
        )


class AbsoluteReportRegionLayoutTests(unittest.TestCase):
    def test_fixed_absolute_regions_resolve_expected_geometry(self) -> None:
        doc: Any = document()
        page = doc.page((400.0, 300.0))
        page.add(Canvas().name("full-page-region").size(400, 300).absolute(0, 0))
        page.add(Frame().name("kpi-region").width(120).height(64).absolute(32, 36))
        page.add(Canvas().name("chart-region").size(220, 110).absolute(150, 120))

        root = _resolve_page_layout(page)

        self.assertEqual(root.resolved_width, 400.0)
        self.assertEqual(root.resolved_height, 300.0)
        self.assertEqual(
            (
                _child_by_name(root, "full-page-region").local_x,
                _child_by_name(root, "full-page-region").local_y,
                _child_by_name(root, "full-page-region").resolved_width,
                _child_by_name(root, "full-page-region").resolved_height,
            ),
            (0.0, 0.0, 400.0, 300.0),
        )
        self.assertEqual(
            (
                _child_by_name(root, "kpi-region").local_x,
                _child_by_name(root, "kpi-region").local_y,
                _child_by_name(root, "kpi-region").resolved_width,
                _child_by_name(root, "kpi-region").resolved_height,
            ),
            (32.0, 36.0, 120.0, 64.0),
        )
        self.assertEqual(
            (
                _child_by_name(root, "chart-region").local_x,
                _child_by_name(root, "chart-region").local_y,
                _child_by_name(root, "chart-region").resolved_width,
                _child_by_name(root, "chart-region").resolved_height,
            ),
            (150.0, 120.0, 220.0, 110.0),
        )

    def test_absolute_regions_do_not_advance_parent_flow_layout(self) -> None:
        doc: Any = document()
        page = doc.page((400.0, 300.0))
        report = Frame().name("report-root").size(360, 200)
        report.add(Canvas().name("absolute-region").size(100, 50).absolute(24, 120))
        report.add(Frame().name("flow-one").size(300, 40))
        report.add(Frame().name("flow-two").size(300, 30))
        page.add(report)

        root = _resolve_page_layout(page)
        report_node = _child_by_name(root, "report-root")
        absolute_region = _child_by_name(report_node, "absolute-region")
        flow_one = _child_by_name(report_node, "flow-one")
        flow_two = _child_by_name(report_node, "flow-two")

        self.assertEqual(report_node.resolved_height, 200.0)
        self.assertEqual((absolute_region.local_x, absolute_region.local_y), (24.0, 120.0))
        self.assertEqual((flow_one.local_x, flow_one.local_y), (0.0, 0.0))
        self.assertEqual((flow_two.local_x, flow_two.local_y), (0.0, 40.0))

    def test_layered_report_shape_uses_predefined_absolute_regions(self) -> None:
        doc: Any = document()
        page = doc.page((600.0, 800.0))
        background = Canvas().name("full-page-background").size(600, 800).absolute(0, 0).z(-10)
        kpi_card = Frame().name("kpi-card-region").size(160, 84).absolute(32, 32).z(2)
        chart = Canvas().name("chart-placeholder-region").width(360).height(210).absolute(208, 150).z(1)
        chart.add_rect().name("chart-plot-area").size(320, 160).absolute(20, 24)
        flow_content = Frame().name("flow-content-region").size(536, 280).absolute(32, 420)
        flow_content.add(Frame().name("flow-row-one").height(42))
        flow_content.add(Frame().name("flow-row-two").height(42))
        page.add(background).add(kpi_card).add(chart).add(flow_content)

        root = _resolve_page_layout(page)
        background_node = _child_by_name(root, "full-page-background")
        kpi_node = _child_by_name(root, "kpi-card-region")
        chart_node = _child_by_name(root, "chart-placeholder-region")
        flow_node = _child_by_name(root, "flow-content-region")
        plot_area = _child_by_name(chart_node, "chart-plot-area")
        flow_row_one = _child_by_name(flow_node, "flow-row-one")
        flow_row_two = _child_by_name(flow_node, "flow-row-two")

        self.assertEqual(
            (background_node.local_x, background_node.local_y, background_node.resolved_width, background_node.resolved_height),
            (0.0, 0.0, 600.0, 800.0),
        )
        self.assertEqual(
            (kpi_node.local_x, kpi_node.local_y, kpi_node.resolved_width, kpi_node.resolved_height),
            (32.0, 32.0, 160.0, 84.0),
        )
        self.assertEqual(
            (chart_node.local_x, chart_node.local_y, chart_node.resolved_width, chart_node.resolved_height),
            (208.0, 150.0, 360.0, 210.0),
        )
        self.assertEqual(
            (flow_node.local_x, flow_node.local_y, flow_node.resolved_width, flow_node.resolved_height),
            (32.0, 420.0, 536.0, 280.0),
        )
        self.assertEqual((plot_area.local_x, plot_area.local_y), (20.0, 24.0))
        self.assertEqual((flow_row_one.local_y, flow_row_two.local_y), (0.0, 42.0))


class TextLinkApiTests(unittest.TestCase):
    def test_text_link_stores_url_and_returns_self(self) -> None:
        text = Text("Example")

        result = text.link("https://example.com")

        self.assertIs(result, text)
        self.assertEqual(text.node.content["text"], "Example")
        self.assertEqual(text.node.content["link_url"], "https://example.com")

    def test_text_without_link_keeps_existing_content_shape(self) -> None:
        text = Text("Plain")

        self.assertEqual(text.node.content, {"text": "Plain"})

    def test_text_link_rejects_non_string_url(self) -> None:
        with self.assertRaisesRegex(TypeError, "link|url"):
            Text("Example").link(cast(Any, 123))

    def test_text_link_rejects_empty_or_whitespace_url(self) -> None:
        for value in ("", "   "):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "link|url"):
                    Text("Example").link(value)


class DocumentSaveToBytesTests(unittest.TestCase):
    def test_document_save_to_bytes_returns_pdf_bytes(self) -> None:
        doc = document()
        doc.page("A4").add_text("Document bytes smoke").absolute(36, 36)

        pdf_bytes = doc.build().save_to_bytes()

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 100)

    def test_document_builder_save_to_bytes_delegates_to_built_document(self) -> None:
        doc = document()
        doc.page("A4").add_text("Builder bytes smoke").absolute(36, 36)

        pdf_bytes = doc.save_to_bytes()

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 100)

    def test_repeated_save_to_bytes_calls_return_valid_pdf_bytes(self) -> None:
        doc = document()
        doc.page("A4").add_text("Repeated bytes smoke").absolute(36, 36)

        first_pdf = doc.save_to_bytes()
        second_pdf = doc.save_to_bytes()

        self.assertTrue(first_pdf.startswith(b"%PDF"))
        self.assertTrue(second_pdf.startswith(b"%PDF"))
        self.assertGreater(len(first_pdf), 100)
        self.assertGreater(len(second_pdf), 100)

    def test_repeated_save_to_bytes_keeps_reserved_overlay_padding_stable(self) -> None:
        doc: Any = document()
        doc.header().height(36).add_text("Stable header").absolute(36, 8)
        doc.footer().height(28).add_text("Stable footer").absolute(36, 8)
        page = doc.page((300.0, 220.0)).padding(12)
        page.add_text("Stable body").name("stable-body")

        first_pdf = doc.save_to_bytes()
        first_padding = page.node.style.padding
        first_base_padding = page.node.content["base_padding"]
        second_pdf = doc.save_to_bytes()
        second_padding = page.node.style.padding
        second_base_padding = page.node.content["base_padding"]

        self.assertTrue(first_pdf.startswith(b"%PDF"))
        self.assertTrue(second_pdf.startswith(b"%PDF"))
        self.assertEqual(
            (first_padding.top, first_padding.right, first_padding.bottom, first_padding.left),
            (36.0, 12.0, 28.0, 12.0),
        )
        self.assertEqual(
            (second_padding.top, second_padding.right, second_padding.bottom, second_padding.left),
            (36.0, 12.0, 28.0, 12.0),
        )
        self.assertEqual(
            (first_base_padding.top, first_base_padding.right, first_base_padding.bottom, first_base_padding.left),
            (12.0, 12.0, 12.0, 12.0),
        )
        self.assertIs(second_base_padding, first_base_padding)

    def test_file_save_still_writes_non_empty_pdf(self) -> None:
        doc = document()
        doc.page("A4").add_text("File save smoke").absolute(36, 36)

        temp_dir, output = _save_temp_pdf(doc, "file_save_still_works.pdf")
        with temp_dir:
            self.assertTrue(output.exists())
            self.assertTrue(output.read_bytes().startswith(b"%PDF"))
            self.assertGreater(output.stat().st_size, 100)


@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class DocumentSaveToBytesPdfTests(unittest.TestCase):
    def test_save_to_bytes_output_can_be_read_and_text_extracted(self) -> None:
        assert PdfReader is not None
        doc = document()
        doc.page("A4").add_text("Hello from save_to_bytes").absolute(36, 36)

        pdf_bytes = doc.save_to_bytes()
        text = _document_text(PdfReader(BytesIO(pdf_bytes)))

        self.assertIn("Hello from save_to_bytes", text)


class DocumentStructureSectionApiTests(unittest.TestCase):
    def test_legacy_page_api_uses_implicit_default_section(self) -> None:
        doc: Any = document()
        page = doc.page("A4")
        built = doc.build()

        self.assertEqual(page.node.content["section_id"], "section-1")
        self.assertEqual(len(built.sections), 1)
        self.assertIsNone(built.sections[0].name)
        self.assertEqual(built.sections[0].page_numbering, "continue")
        self.assertFalse(built.sections[0].outline)
        self.assertEqual(built.sections[0].pages, [page.node])

    def test_section_page_api_tags_pages_with_section_id(self) -> None:
        doc: Any = document()
        section = doc.section("Intro")
        page = section.page("A4")
        built = doc.build()

        self.assertEqual(page.node.content["section_id"], "section-1")
        self.assertEqual(built.sections[0].section_id, "section-1")
        self.assertEqual(built.sections[0].name, "Intro")
        self.assertEqual(built.sections[0].page_numbering, "restart")
        self.assertTrue(built.sections[0].outline)
        self.assertEqual(built.sections[0].pages, [page.node])

    def test_invalid_section_page_numbering_raises_value_error(self) -> None:
        doc: Any = document()

        with self.assertRaisesRegex(ValueError, "Unsupported section page numbering"):
            doc.section("Intro", page_numbering="roman")

    def test_section_overlays_and_suppression_are_stored_on_section(self) -> None:
        doc: Any = document()
        section = doc.section("Intro")
        section.header()
        section.footer()
        section.watermark()
        section.suppress_header().suppress_footer().suppress_watermark()
        built = doc.build()
        built_section = built.sections[0]

        self.assertEqual([node.name for node in built_section.overlay_templates["header"]], ["__doc_header__"])
        self.assertEqual([node.name for node in built_section.overlay_templates["footer"]], ["__doc_footer__"])
        self.assertEqual([node.name for node in built_section.overlay_templates["watermark"]], ["__doc_watermark__"])
        self.assertEqual(built.overlay_templates, {"header": [], "footer": [], "watermark": []})
        self.assertEqual(built_section.suppressed_overlays, {"header", "footer", "watermark"})

    def test_empty_section_does_not_make_save_fail_when_pages_exist(self) -> None:
        doc: Any = document()
        doc.section("Empty Preface")
        _fill_section_page(doc.page("A4"), "Legacy")

        temp_dir, output = _save_temp_pdf(doc, "empty_section_api.pdf")
        with temp_dir:
            self.assertTrue(output.exists())

    def test_metadata_calls_merge_only_non_none_fields(self) -> None:
        doc: Any = document()
        result = doc.metadata(title="Initial", author="Author").metadata(title=None, subject="Subject")
        built = doc.build()

        self.assertIs(result, doc)
        self.assertEqual(built.metadata, {"title": "Initial", "author": "Author", "subject": "Subject"})


class DocumentOverlayRenderOrderTests(unittest.TestCase):
    def test_document_overlays_render_around_layered_page_content(self) -> None:
        doc: Any = document()
        doc.watermark().height(80).add_text("Document watermark").name("document-watermark-label").absolute(40, 20)
        doc.header().height(30).add_text("Document header").name("document-header-label").absolute(24, 8)
        doc.footer().height(24).add_text("Document footer").name("document-footer-label").absolute(24, 8)
        page = doc.page((360.0, 240.0))
        page.add(Canvas().name("page-underlay").size(320, 120).absolute(20, 50).z(-20))
        body = Frame().name("page-content").padding(10)
        body.add_text("Layered body content").name("body-label")
        page.add(body)
        page.add(Canvas().name("page-overlay").size(320, 40).absolute(20, 90).z(20))

        names_by_page = _painted_names_by_page_from_save_to_bytes(doc)
        layered_names = [
            name
            for name in names_by_page[0]
            if name
            in {
                "__doc_watermark__",
                "document-watermark-label",
                "page-underlay",
                "page-content",
                "body-label",
                "page-overlay",
                "__doc_header__",
                "document-header-label",
                "__doc_footer__",
                "document-footer-label",
            }
        ]

        self.assertEqual(
            layered_names,
            [
                "__doc_watermark__",
                "document-watermark-label",
                "page-underlay",
                "page-content",
                "body-label",
                "page-overlay",
                "__doc_header__",
                "document-header-label",
                "__doc_footer__",
                "document-footer-label",
            ],
        )

    def test_section_overlay_override_keeps_unspecified_document_overlay_fallbacks(self) -> None:
        doc: Any = document()
        doc.watermark().height(60).add_text("Global watermark").name("global-watermark-label").absolute(40, 20)
        doc.header().height(24).add_text("Global header").name("global-header-label").absolute(24, 8)
        doc.footer().height(24).add_text("Global footer").name("global-footer-label").absolute(24, 8)
        fallback = doc.section("Fallback")
        fallback.page((300.0, 220.0)).add_text("Fallback body").name("fallback-body")
        override = doc.section("Override")
        override.header().height(24).add_text("Section header").name("section-header-label").absolute(24, 8)
        override.page((300.0, 220.0)).add_text("Override body").name("override-body")

        names_by_page = _painted_names_by_page_from_save_to_bytes(doc)

        self.assertEqual(len(names_by_page), 2)
        self.assertIn("global-watermark-label", names_by_page[0])
        self.assertIn("global-header-label", names_by_page[0])
        self.assertIn("global-footer-label", names_by_page[0])
        self.assertIn("fallback-body", names_by_page[0])
        self.assertIn("global-watermark-label", names_by_page[1])
        self.assertNotIn("global-header-label", names_by_page[1])
        self.assertIn("section-header-label", names_by_page[1])
        self.assertIn("global-footer-label", names_by_page[1])
        self.assertIn("override-body", names_by_page[1])


@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class DocumentOverlayTests(unittest.TestCase):
    def test_legacy_page_api_keeps_global_overlays_and_page_placeholders(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.header().height(24).add_text("Legacy header {page_number}/{total_pages}").absolute(36, 8)
        doc.footer().height(24).add_text("Legacy footer {page_number}/{total_pages}").absolute(36, 8)
        doc.watermark().height(80).add_text("Legacy watermark").absolute(180, 20)
        _fill_section_page(doc.page("A4"), "Legacy")

        temp_dir, output = _save_temp_pdf(doc, "legacy_placeholders.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertIn("Legacy header 1/1", text)
        self.assertIn("Legacy footer 1/1", text)
        self.assertIn("Legacy watermark", text)
        self.assertIn("Legacy body line 1", text)

    def test_section_overlay_falls_back_to_document_overlay(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.header().height(24).add_text("Global header").absolute(36, 8)
        section = doc.section("Fallback")
        _fill_section_page(section.page("A4"), "Fallback")

        temp_dir, output = _save_temp_pdf(doc, "overlay_fallback.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertIn("Global header", text)
        self.assertIn("Fallback body line 1", text)

    def test_section_overlay_overrides_document_overlay(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.header().height(24).add_text("Global header").absolute(36, 8)
        section = doc.section("Override")
        section.header().height(24).add_text("Section header").absolute(36, 8)
        _fill_section_page(section.page("A4"), "Override")

        temp_dir, output = _save_temp_pdf(doc, "overlay_override.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertIn("Section header", text)
        self.assertNotIn("Global header", text)

    def test_section_overlay_suppression_removes_inherited_overlays(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.header().height(24).add_text("Global header").absolute(36, 8)
        doc.footer().height(24).add_text("Global footer").absolute(36, 8)
        doc.watermark().height(80).add_text("Global watermark").absolute(180, 20)
        section = doc.section("Suppressed")
        section.suppress_header()
        section.suppress_footer()
        section.suppress_watermark()
        _fill_section_page(section.page("A4"), "Suppressed")

        temp_dir, output = _save_temp_pdf(doc, "overlay_suppression.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertNotIn("Global header", text)
        self.assertNotIn("Global footer", text)
        self.assertNotIn("Global watermark", text)
        self.assertIn("Suppressed body line 1", text)

    def test_section_multiple_headers_are_all_rendered(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        section = doc.section("Multiple Headers")
        section.header().height(12).add_text("Section header A").absolute(36, 2)
        section.header().height(12).add_text("Section header B").absolute(180, 2)
        _fill_section_page(section.page("A4"), "Multiple")

        temp_dir, output = _save_temp_pdf(doc, "overlay_multiple_headers.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertIn("Section header A", text)
        self.assertIn("Section header B", text)
        self.assertIn("Multiple body line 1", text)


@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class DocumentSectionNumberingTests(unittest.TestCase):
    def test_section_page_numbering_restart_affects_page_placeholders(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.footer().height(24).add_text(
            "{section_name} section {section_page_number}/{section_total_pages} absolute {page_number}/{total_pages}"
        ).absolute(36, 8)
        first = doc.section("First", page_numbering="restart")
        _fill_section_page(first.page("A4"), "First", count=60)
        second = doc.section("Second", page_numbering="restart")
        _fill_section_page(second.page("A4"), "Second")

        temp_dir, output = _save_temp_pdf(doc, "section_numbering.pdf")
        with temp_dir:
            texts = _page_texts(PdfReader(str(output)))

        self.assertEqual(len(texts), 3)
        self.assertIn("First section 1/2 absolute 1/3", texts[0])
        self.assertIn("First section 2/2 absolute 2/3", texts[1])
        self.assertIn("Second section 1/1 absolute 3/3", texts[2])

    def test_section_page_numbering_continue_joins_current_numbering_group(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.footer().height(24).add_text(
            "{section_name} continued {section_page_number}/{section_total_pages} absolute {page_number}/{total_pages}"
        ).absolute(36, 8)
        first = doc.section("First", page_numbering="restart")
        _fill_section_page(first.page("A4"), "First", count=60)
        second = doc.section("Second", page_numbering="continue")
        second_page = second.page("A4")
        second_page.add_text(
            "Second body {section_page_number}/{section_total_pages} absolute {page_number}/{total_pages}"
        ).absolute(36, 80)

        temp_dir, output = _save_temp_pdf(doc, "section_numbering_continue.pdf")
        with temp_dir:
            texts = _page_texts(PdfReader(str(output)))

        self.assertEqual(len(texts), 3)
        self.assertIn("First continued 1/3 absolute 1/3", texts[0])
        self.assertIn("First continued 2/3 absolute 2/3", texts[1])
        self.assertIn("Second continued 3/3 absolute 3/3", texts[2])
        self.assertIn("Second body 3/3 absolute 3/3", texts[2])

    def test_section_placeholders_work_in_page_content_and_overlays(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        section = doc.section("Content Section", page_numbering="restart")
        section.header().height(24).add_text(
            "Header {section_name} {section_page_number}/{section_total_pages}"
        ).absolute(36, 8)
        page = section.page("A4")
        page.add_text(
            "Body {section_name} {section_page_number}/{section_total_pages} absolute {page_number}/{total_pages}"
        ).absolute(36, 80)

        temp_dir, output = _save_temp_pdf(doc, "section_placeholders.pdf")
        with temp_dir:
            text = _document_text(PdfReader(str(output)))

        self.assertIn("Header Content Section 1/1", text)
        self.assertIn("Body Content Section 1/1 absolute 1/1", text)


@unittest.skipIf(PdfReader is None, "pypdf is not installed")
class DocumentStructurePdfTests(unittest.TestCase):
    def test_section_overlay_falls_back_to_document_overlay(self) -> None:
        DocumentOverlayTests("test_section_overlay_falls_back_to_document_overlay").test_section_overlay_falls_back_to_document_overlay()

    def test_section_overlay_overrides_document_overlay(self) -> None:
        DocumentOverlayTests("test_section_overlay_overrides_document_overlay").test_section_overlay_overrides_document_overlay()

    def test_section_overlay_suppression_removes_inherited_overlays(self) -> None:
        DocumentOverlayTests("test_section_overlay_suppression_removes_inherited_overlays").test_section_overlay_suppression_removes_inherited_overlays()

    def test_multiple_sections_render_in_document_order_with_named_outlines(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        first = doc.section("Executive Summary", outline=True)
        _fill_section_page(first.page("A4"), "Executive")
        second = doc.section("Appendix", outline=True)
        _fill_section_page(second.page("A4"), "Appendix")

        temp_dir, output = _save_temp_pdf(doc, "multiple_sections.pdf")
        with temp_dir:
            reader = PdfReader(str(output))
            text = _document_text(reader)
            outlines = _outline_titles(reader)

        self.assertLess(text.index("Executive body line 1"), text.index("Appendix body line 1"))
        self.assertEqual(outlines, ["Executive Summary", "Appendix"])

    def test_metadata_is_written_to_pdf_info_dictionary(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.metadata(title="V2.4 Report", author="smart-report", subject="Document structure", keywords="sections, outlines")
        _fill_section_page(doc.page("A4"), "Metadata")

        temp_dir, output = _save_temp_pdf(doc, "metadata.pdf")
        with temp_dir:
            reader = PdfReader(str(output))
            self.assertEqual(_metadata_value(reader, "title"), "V2.4 Report")
            self.assertEqual(_metadata_value(reader, "author"), "smart-report")
            self.assertEqual(_metadata_value(reader, "subject"), "Document structure")
            self.assertEqual(_metadata_value(reader, "keywords"), "sections, outlines")

    def test_section_page_numbering_restart_affects_page_placeholders(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.footer().height(24).add_text("Page {section_page_number} of {section_total_pages}").absolute(36, 8)
        first = doc.section("First", page_numbering="restart")
        _fill_section_page(first.page("A4"), "First")
        second = doc.section("Second", page_numbering="restart")
        _fill_section_page(second.page("A4"), "Second")

        temp_dir, output = _save_temp_pdf(doc, "section_numbering.pdf")
        with temp_dir:
            texts = _page_texts(PdfReader(str(output)))

        self.assertEqual(len(texts), 2)
        self.assertTrue(all("Page 1 of 1" in text for text in texts))

    def test_empty_section_emits_no_outline_entry_or_blank_page(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.section("Empty Preface", outline=True)
        content = doc.section("Content", outline=True)
        _fill_section_page(content.page("A4"), "Content")

        temp_dir, output = _save_temp_pdf(doc, "empty_section.pdf")
        with temp_dir:
            reader = PdfReader(str(output))
            outlines = _outline_titles(reader)

        self.assertEqual(len(reader.pages), 1)
        self.assertEqual(outlines, ["Content"])

    def test_outline_false_section_emits_no_outline_entry(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        hidden = doc.section("Hidden", outline=False)
        _fill_section_page(hidden.page("A4"), "Hidden")
        visible = doc.section("Visible", outline=True)
        _fill_section_page(visible.page("A4"), "Visible")

        temp_dir, output = _save_temp_pdf(doc, "outline_false.pdf")
        with temp_dir:
            outlines = _outline_titles(PdfReader(str(output)))

        self.assertEqual(outlines, ["Visible"])

    def test_single_line_linked_text_emits_one_url_annotation(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.page("A4").add_text("Example linked text").absolute(36, 36).width(240).link("https://example.com")

        temp_dir, output = _save_temp_pdf(doc, "single_text_link.pdf")
        with temp_dir:
            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertEqual(page_uris, [["https://example.com"]])

    def test_wrapped_linked_text_emits_one_url_annotation_per_line(self) -> None:
        assert PdfReader is not None
        text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"
        width = 90.0
        font_size = 12.0
        expected_lines = wrap_text(text, width, "Helvetica", font_size)
        self.assertGreater(len(expected_lines), 1)
        doc: Any = document()
        doc.page("A4").add_text(text).absolute(36, 36).width(width).font_size(font_size).line_height(14).link("https://example.com/wrapped")

        temp_dir, output = _save_temp_pdf(doc, "wrapped_text_link.pdf")
        with temp_dir:
            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertEqual(page_uris, [["https://example.com/wrapped"] * len(expected_lines)])

    def test_unlinked_text_emits_no_url_annotations(self) -> None:
        assert PdfReader is not None
        doc: Any = document()
        doc.page("A4").add_text("Plain text only").absolute(36, 36).width(240)

        temp_dir, output = _save_temp_pdf(doc, "plain_text_no_link.pdf")
        with temp_dir:
            page_uris = _page_link_annotation_uris(PdfReader(str(output)))

        self.assertEqual(page_uris, [[]])

    def test_paginated_linked_text_keeps_url_annotations_on_split_pages(self) -> None:
        assert PdfReader is not None
        linked_lines = "\n".join(f"Linked line {index}" for index in range(1, 90))
        doc: Any = document()
        frame = Frame().padding(36)
        frame.add_text(linked_lines).font_size(12).line_height(16).link("https://example.com/paginated")
        doc.page("A4").add(frame)

        temp_dir, output = _save_temp_pdf(doc, "paginated_text_link.pdf")
        with temp_dir:
            reader = PdfReader(str(output))
            page_uris = _page_link_annotation_uris(reader)

        self.assertGreater(len(page_uris), 1)
        self.assertTrue(all(uris for uris in page_uris))
        self.assertTrue(all(uri == "https://example.com/paginated" for uris in page_uris for uri in uris))


class _FakeCanvas:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def setTitle(self, value: str) -> None:
        self.calls.append(("setTitle", (value,)))

    def setAuthor(self, value: str) -> None:
        self.calls.append(("setAuthor", (value,)))

    def setSubject(self, value: str) -> None:
        self.calls.append(("setSubject", (value,)))

    def setKeywords(self, value: str) -> None:
        self.calls.append(("setKeywords", (value,)))

    def bookmarkPage(self, key: str) -> None:
        self.calls.append(("bookmarkPage", (key,)))

    def addOutlineEntry(self, title: str, key: str, level: int = 0, closed: bool = False) -> None:
        self.calls.append(("addOutlineEntry", (title, key, level, closed)))

    def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:
        self.calls.append(("linkURL", (url, rect), {"relative": relative}))


class DocumentStructureAdapterTests(unittest.TestCase):
    def test_adapter_metadata_wrapper_delegates_to_reportlab_canvas(self) -> None:
        adapter = cast(Any, ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter))
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.set_metadata(title="Report", author="Author", subject="Subject", keywords="alpha, beta")

        self.assertEqual(
            fake_canvas.calls,
            [
                ("setTitle", ("Report",)),
                ("setAuthor", ("Author",)),
                ("setSubject", ("Subject",)),
                ("setKeywords", ("alpha, beta",)),
            ],
        )

    def test_adapter_bookmark_page_wrapper_delegates_to_reportlab_canvas(self) -> None:
        adapter = cast(Any, ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter))
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.bookmark_page("section-1")

        self.assertEqual(fake_canvas.calls, [("bookmarkPage", ("section-1",))])

    def test_adapter_outline_entry_wrapper_delegates_to_reportlab_canvas(self) -> None:
        adapter = cast(Any, ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter))
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.add_outline_entry("Executive Summary", "section-1", level=0)

        self.assertEqual(fake_canvas.calls, [("addOutlineEntry", ("Executive Summary", "section-1", 0, False))])

    def test_adapter_link_url_wrapper_converts_top_left_rect_to_reportlab_rect(self) -> None:
        adapter = cast(Any, ReportLabCanvasAdapter.__new__(ReportLabCanvasAdapter))
        fake_canvas = _FakeCanvas()
        adapter._canvas = fake_canvas
        adapter.page_width = 200
        adapter.page_height = 100

        adapter.link_url("https://example.com", Rect(x=10, y=20, width=30, height=40))

        self.assertEqual(
            fake_canvas.calls,
            [("linkURL", ("https://example.com", (10, 40, 40, 80)), {"relative": 0})],
        )


if __name__ == "__main__":
    unittest.main()
