"""Regression tests for planned v2.4 document structure APIs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from smart_report import Frame, Text, document
from smart_report.layout.node import Rect
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
