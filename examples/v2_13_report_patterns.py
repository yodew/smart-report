"""v2.13 report section and card pattern recipes on one A4 page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smart_report import Canvas, Frame, Table, document


PAGE_WIDTH = 595.2756
PAGE_HEIGHT = 841.8898
CONTENT_LEFT = 36
CONTENT_WIDTH = 523

EXAMPLE_DIR = Path(__file__).resolve().parent
COVER_IMAGE = EXAMPLE_DIR / "cover.jpg"
BOX_IMAGE = EXAMPLE_DIR / "box.png"
OUTPUT_PDF = EXAMPLE_DIR / "v2_13_report_patterns.pdf"


def add_pill(canvas: Canvas, text: str, left: float, top: float, background: str, color: str = "#ffffff") -> None:
    canvas.add_rect(text).absolute(left, top).padding(vertical=4, horizontal=9).background(background).color(color).font_size(7.8).line_height(10).radius(999).z(8)


def kpi_card(label: str, value: str, detail: str, accent: str, note: str) -> Canvas:
    card = Canvas().size(162, 88).background("#ffffff").stroke("#d7dee8", 0.8).radius(16).z(20)
    card.add_rect().absolute(0, 0).size(162, 88).background("#ffffff").radius(16).z(0)
    card.add_rect().absolute(0, 0).size(5, 88).background(accent).radius((16, 0, 0, 16)).z(1)
    card.add_text(label).absolute(17, 13).font_size(8.2).line_height(10).color("#64748b").z(2)
    card.add_text(value).absolute(17, 31).font_size(21).line_height(24).color("#0f172a").z(2)
    card.add_text(detail).absolute(17, 59).font_size(8.6).line_height(11).color(accent).z(2)
    card.add_text(note).absolute(102, 15).width(44).font_size(7.2).line_height(9).color("#94a3b8").z(2)
    return card


def insight_card(title: str, body: str, accent: str, left: float, top: float, width: float, height: float) -> Canvas:
    card = Canvas().size(width, height).absolute(left, top).background("#ffffff").stroke("#d7dee8", 0.8).radius(15).z(20)
    card.add_rect().absolute(14, 16).size(4, height - 32).background(accent).radius(999).z(1)
    card.add_text(title).absolute(28, 16).width(width - 46).font_size(11.2).line_height(14).color("#0f172a").z(3)
    card.add_text(body).absolute(28, 38).width(width - 46).font_size(7.8).line_height(10.2).color("#475569").z(3)
    card.add_line().absolute(18, height - 14).size(width - 36, 0).stroke("#e2e8f0", 0.7).z(3)
    return card


def add_page_background(page: Any) -> None:
    background = Canvas().name("v2-13-page-background").size(PAGE_WIDTH, PAGE_HEIGHT).absolute(0, 0).z(-30)
    background.add_rect().absolute(0, 0).size(PAGE_WIDTH, PAGE_HEIGHT).background("#edf2f5").z(0)
    background.add_rect().absolute(28, 118).size(539, 690).background("#ffffff").opacity(0.60).radius(28).z(1)
    background.add_rect().absolute(392, 20).size(154, 96).background("#f59e0b").opacity(0.14).radius(28).z(2)
    background.add_rect().absolute(24, 682).size(204, 78).background("#0f766e").opacity(0.07).radius(28).z(2)
    page.add(background)


def add_hero(page: Any) -> None:
    hero = Canvas().name("background-image-report-hero").size(CONTENT_WIDTH, 144).absolute(CONTENT_LEFT, 30).background("#10243f").background_image(COVER_IMAGE, fit="cover", opacity=0.48).stroke("#1e293b", 1).radius(22).overflow("hidden").z(10)
    hero.add_rect().absolute(0, 0).size(CONTENT_WIDTH, 144).background("rgba(15,23,42,0.50)").z(1)
    hero.add_rect().absolute(0, 0).size(190, 144).background("rgba(15,23,42,0.34)").z(2)
    add_pill(hero, "REPORT SECTION RECIPES", 24, 22, "#f59e0b", "#111827")
    hero.add_text("Operating Review Patterns").absolute(24, 52).width(330).font_size(27).line_height(32).color("#ffffff").z(3)
    hero.add_text("A report-ready hero, KPI strip, executive summary card, annotated data table, and dashboard card grid composed only from existing smart-report primitives.").absolute(24, 92).width(356).font_size(9.8).line_height(13.5).color("#dbeafe").z(3)
    hero.add_rect("v2.13.0").absolute(418, 24).padding(vertical=6, horizontal=12).background("rgba(255,255,255,0.90)").color("#0f172a").font_size(9).line_height(11).radius(999).z(4)
    hero.add_text("A4 / business report").absolute(410, 108).width(88).font_size(8.2).line_height(10.5).color("#cbd5e1").z(4)
    page.add(hero)


def add_kpi_strip(page: Any) -> None:
    cards = [
        kpi_card("Net revenue", "$4.82M", "+18% vs plan", "#0f766e", "renewals ahead"),
        kpi_card("Pipeline cover", "3.4x", "+0.6x QoQ", "#2563eb", "next 90 days"),
        kpi_card("Risk exposure", "7.2%", "-1.8 pts", "#f97316", "watch list"),
    ]
    for index, card in enumerate(cards):
        card.absolute(CONTENT_LEFT + index * 180.5, 194)
        page.add(card)


def add_executive_summary(page: Any) -> None:
    summary = Canvas().name("image-text-executive-summary-card").size(CONTENT_WIDTH, 150).absolute(CONTENT_LEFT, 306).background("#ffffff").stroke("#d7dee8", 0.8).radius(20).overflow("hidden").z(20)
    summary.add_image(str(COVER_IMAGE)).absolute(0, 0).size(186, 150).cover().radius((20, 0, 0, 20)).z(1)
    summary.add_rect().absolute(160, 0).size(48, 150).background("rgba(255,255,255,0.88)").z(2)
    add_pill(summary, "EXECUTIVE SUMMARY", 222, 18, "#0f766e")
    summary.add_text("Broad momentum; isolate margin leakage before scaling the operating plan.").absolute(222, 45).width(274).font_size(13.8).line_height(16.5).color("#0f172a").z(3)
    (
        summary.add_rich_text()
        .absolute(222, 102)
        .width(266)
        .font_size(8.4)
        .line_height(11.5)
        .span("Use when leadership needs ", color="#475569")
        .span("one decisive takeaway", color="#0f766e", bold=True)
        .span(" beside visual proof. The card is just Image, Rect, Text, and RichText layered inside a Canvas.", color="#475569")
        .z(3)
    )
    page.add(summary)


def add_table_section(page: Any) -> None:
    section = Canvas().name("data-table-with-explanatory-copy").size(CONTENT_WIDTH, 154).absolute(CONTENT_LEFT, 474).background("#f8fafc").stroke("#d7dee8", 0.8).radius(18).z(20)
    section.add_text("Regional execution table").absolute(18, 16).font_size(14.5).line_height(18).color("#0f172a").z(2)
    section.add_text("Pair a compact table with direct interpretation so readers can scan the action without decoding every number.").absolute(18, 40).width(468).font_size(8.4).line_height(11.5).color("#475569").z(2)
    section.add(
        Table([
            ["Region", "Revenue", "Growth", "Action"],
            ["North America", "$1.72M", "+21%", "Renew enterprise base."],
            ["EMEA", "$1.14M", "+12%", "Package proof points."],
            ["APAC", "$1.32M", "+19%", "Scale partner plays."],
        ])
        .absolute(18, 66)
        .column_widths([98, 70, 56, 240])
        .align(["left", "right", "right", "left"])
        .cell_padding(vertical=3.5, horizontal=8)
        .header(background="rgba(15,23,42,0.94)", color="#ffffff")
        .zebra("rgba(255,255,255,0.70)")
        .column_style(2, color="#0f766e")
        .cell_style(1, 1, background="#ecfdf5", color="#065f46", align="right")
        .font_size(7.8)
        .line_height(9.7)
        .color("#1e293b")
        .background_image(BOX_IMAGE, fit="cover", opacity=0.12)
        .borders("rgba(203,213,225,0.74)", width=0.45)
        .z(3)
    )
    page.add(section)


def add_dashboard_cards(page: Any) -> None:
    heading = Frame().name("dashboard-card-section-heading").size(CONTENT_WIDTH, 38).absolute(CONTENT_LEFT, 642).padding(0).z(20)
    heading.add_text("Multi-card report section layout").font_size(14.5).line_height(18).color("#0f172a").margin(bottom=4)
    heading.add_text("Use repeated fixed cards for decision prompts and status notes without custom components.").font_size(8.4).line_height(10.8).color("#64748b")
    page.add(heading)

    cards = [
        ("Decision", "Shift onboarding toward APAC partners before renewals.", "#0f766e", CONTENT_LEFT, 684, 162, 78),
        ("Watch", "Package EMEA proof points before late-stage reviews.", "#f97316", CONTENT_LEFT + 180.5, 684, 162, 78),
        ("Repeat", "Keep summary cards on page one; move detail tables later.", "#2563eb", CONTENT_LEFT + 361, 684, 162, 78),
    ]
    for title, body, accent, left, top, width, height in cards:
        page.add(insight_card(title, body, accent, left, top, width, height))


def build_report() -> None:
    doc = document()
    page = doc.page("A4")

    add_page_background(page)
    add_hero(page)
    add_kpi_strip(page)
    add_executive_summary(page)
    add_table_section(page)
    add_dashboard_cards(page)

    doc.save(str(OUTPUT_PDF))
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    build_report()
