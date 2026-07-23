"""Practical v2.12 image/text composition patterns on one A4 report page."""

from __future__ import annotations

from pathlib import Path

from smart_report import Canvas, Frame, Table, document


PAGE_WIDTH = 595.2756
PAGE_HEIGHT = 841.8898
CONTENT_LEFT = 36
CONTENT_WIDTH = 523

EXAMPLE_DIR = Path(__file__).resolve().parent
COVER_IMAGE = EXAMPLE_DIR / "cover.jpg"
BOX_IMAGE = EXAMPLE_DIR / "box.png"
BOX_CROP_IMAGE = EXAMPLE_DIR / "box_middle_crop.png"
OUTPUT_PDF = EXAMPLE_DIR / "v2_12_image_text_composition.pdf"


def add_label(canvas: Canvas, text: str, left: float, top: float, accent: str) -> None:
    canvas.add_rect(text).absolute(left, top).padding(vertical=4, horizontal=9).background(accent).color("#ffffff").font_size(8).line_height(10).radius(999).z(5)


def add_body_copy(frame: Frame, title: str, body: str, accent: str) -> None:
    frame.add_text(title).font_size(14).line_height(18).color("#0f172a").margin(bottom=7)
    frame.add_text(body).font_size(9).line_height(13).color("#475569").margin(bottom=10)
    frame.add_rect("image + text, no helper API").padding(vertical=4, horizontal=8).background(accent).color("#ffffff").font_size(8).line_height(10).radius(999)


def build_report() -> None:
    doc = document()
    page = doc.page("A4")

    background = Canvas().name("composition-page-background").size(PAGE_WIDTH, PAGE_HEIGHT).absolute(0, 0).z(-20)
    background.add_rect().absolute(0, 0).size(PAGE_WIDTH, PAGE_HEIGHT).background("#eef4f8").z(0)
    background.add_rect().absolute(0, 0).size(PAGE_WIDTH, 176).background("#0f2236").z(1)
    background.add_rect().absolute(384, 24).size(154, 112).background("#2dd4bf").opacity(0.16).radius(30).z(2)
    background.add_rect().absolute(24, 250).size(548, 538).background("#ffffff").opacity(0.62).radius(28).z(3)
    page.add(background)

    title = Canvas().name("composition-title").size(CONTENT_WIDTH, 86).absolute(CONTENT_LEFT, 40).z(10)
    title.add_text("Image + Text Composition").absolute(0, 0).font_size(27).line_height(32).color("#ffffff").z(2)
    title.add_text("Practical report blocks built from Canvas, Frame, Image, Text, and Table background images.").absolute(0, 38).width(330).font_size(10).line_height(14).color("#cbd5e1").z(2)
    title.add_rect("v2.12.3 example").absolute(393, 8).padding(vertical=6, horizontal=12).background("#14b8a6").color("#ffffff").font_size(9).line_height(11).radius(999).z(3)
    page.add(title)

    side_card = Canvas().name("left-image-right-text-card").size(CONTENT_WIDTH, 154).absolute(CONTENT_LEFT, 142).background("#ffffff").stroke("#dbe3ee", 1).radius(20).overflow("hidden").z(20)
    side_card.add_image(str(COVER_IMAGE)).absolute(0, 0).size(206, 154).cover().radius((20, 0, 0, 20)).z(1)
    side_card.add_rect().absolute(182, 0).size(36, 154).background("#ffffff").opacity(0.86).z(2)
    add_label(side_card, "LEFT IMAGE / RIGHT TEXT", 232, 19, "#0f766e")
    side_card.add_text("Narrative image card").absolute(232, 47).width(242).font_size(18).line_height(23).color("#0f172a").z(3)
    side_card.add_text("Use a fixed Canvas when the image crop and the copy block must stay locked together. The image is an ordinary Image node, while text and badges are positioned on the same layer.").absolute(232, 80).width(248).font_size(10).line_height(14).color("#475569").z(3)
    side_card.add_line().absolute(232, 126).size(214, 0).stroke("#cbd5e1", 0.8).z(3)
    side_card.add_text("Works well for case studies, profile cards, and executive summaries.").absolute(232, 134).width(240).font_size(8).line_height(10).color("#0f766e").z(3)
    page.add(side_card)

    stacked_card = Canvas().name("top-image-bottom-text-card").size(250, 214).absolute(CONTENT_LEFT, 318).background("#ffffff").stroke("#dbe3ee", 1).radius(20).overflow("hidden").z(20)
    stacked_card.add_image(str(COVER_IMAGE)).absolute(0, 0).size(250, 104).cover().radius((20, 20, 0, 0)).z(1)
    copy = Frame().absolute(0, 104).size(250, 110).padding(top=14, right=16, bottom=14, left=16).z(2)
    add_body_copy(copy, "Top image, flowing copy", "Let the image sit first in normal flow, then stack text underneath. This keeps simple marketing-style cards readable and easy to maintain.", "#2563eb")
    stacked_card.add(copy)
    page.add(stacked_card)

    overlay_card = Canvas().name("background-image-title-card").size(250, 214).absolute(309, 318).background("#0f172a").background_image(COVER_IMAGE, fit="cover", opacity=0.58).stroke("#1e293b", 1).radius(20).overflow("hidden").z(20)
    overlay_card.add_rect().absolute(0, 0).size(250, 214).background("rgba(15,23,42,0.38)").z(1)
    add_label(overlay_card, "BACKGROUND IMAGE OVERLAY", 18, 18, "#f97316")
    overlay_card.add_text("Title over photography").absolute(18, 74).width(198).font_size(22).line_height(27).color("#ffffff").z(3)
    overlay_card.add_text("`.background_image(...)` keeps the photograph beneath text, badges, and borders, so overlays stay compact without manual image layering.").absolute(18, 135).width(206).font_size(9).line_height(13).color("#e2e8f0").z(3)
    page.add(overlay_card)

    table_panel = Canvas().name("table-over-background-report-block").size(CONTENT_WIDTH, 226).absolute(CONTENT_LEFT, 558).background("#f8fafc").stroke("#dbe3ee", 1).radius(20).z(20)
    table_panel.add_text("Table over background report block").absolute(18, 16).font_size(16).line_height(21).color("#0f172a").z(2)
    table_panel.add_text("A table-level background image works like a controlled watermark: it spans the table once while cell fills, content, and borders remain legible above it.").absolute(18, 42).width(470).font_size(9).line_height(13).color("#475569").z(2)
    table_panel.add(
        Table([
            ["Pattern", "Best fit", "Implementation cue"],
            ["Side card", "Editorial summaries", "Canvas + absolute Image/Text"],
            ["Stacked card", "Reusable content blocks", "Frame flow with Image first"],
            ["Photo title", "Section openers", "Frame/Canvas.background_image"],
            ["Data block", "KPI tables", "Table.background_image"],
        ])
        .absolute(18, 76)
        .column_widths([116, 134, "auto"])
        .align(["left", "left", "left"])
        .cell_padding(vertical=8, horizontal=10)
        .header(background="rgba(15,23,42,0.92)", color="#ffffff")
        .zebra("rgba(255,255,255,0.58)")
        .font_size(8.7)
        .line_height(11.5)
        .color("#1e293b")
        .column_style(0, color="#0f766e")
        .background_image(BOX_IMAGE, fit="cover", opacity=0.26)
        .borders("#cbd5e1", width=0.7)
        .radius(14)
        .z(3)
    )
    page.add(table_panel)

    doc.save(str(OUTPUT_PDF))
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    build_report()
