"""Generate a practical v2.11 layered report PDF with fixed regions."""

from __future__ import annotations

from typing import Any

from smart_report import Canvas, Frame, Table, document


PAGE_WIDTH = 595.2756
PAGE_HEIGHT = 841.8898


def add_kpi_card(page: Any, left: float, top: float, label: str, value: str, detail: str) -> None:
    card = Frame().size(158, 86).absolute(left, top).padding(vertical=10, horizontal=12).background("#ffffff").stroke("#dbe3ee", 1).radius(14).z(20)
    card.add_text(label).font_size(9).line_height(12).color("#64748b").margin(bottom=8)
    card.add_text(value).font_size(22).line_height(26).color("#0f172a").margin(bottom=5)
    card.add_text(detail).font_size(9).line_height(12).color("#0f766e")
    page.add(card)


def build_report() -> None:
    doc = document()

    header = doc.header().height(54).z(220)
    header.add_rect().absolute(0, 0).size("100%", 54).background("#ffffff").opacity(0.96).z(0)
    header.add_text("v2.11 Layered Report").absolute(36, 17).font_size(15).line_height(18).color("#0f172a").z(2)
    header.add_text("Layered dashboard template").absolute(405, 19).font_size(9).line_height(12).color("#64748b").z(2)
    header.add_line().absolute(36, 52).size(523, 0).stroke("#cbd5e1", 0.8).z(3)

    footer = doc.footer().height(34).z(230)
    footer.add_rect().absolute(0, 0).size("100%", 34).background("#ffffff").opacity(0.94).z(0)
    footer.add_text("Confidential - Finance Strategy Pack").absolute(36, 10).font_size(8).line_height(10).color("#64748b").z(2)
    footer.add_text("Page {page_number} / {total_pages}").absolute(486, 10).font_size(8).line_height(10).color("#64748b").z(2)

    watermark = doc.watermark().height(PAGE_HEIGHT).opacity(0.07).z(90)
    watermark.add_text("Confidential").absolute(176, 386).font_size(52).line_height(58).color("#0f172a").z(1)

    page = doc.page("A4")

    background = Canvas().name("full-page-background").size(PAGE_WIDTH, PAGE_HEIGHT).absolute(0, 0).z(-20)
    background.add_rect().absolute(0, 0).size(PAGE_WIDTH, PAGE_HEIGHT).background("#f4f7fb").z(0)
    background.add_rect().absolute(0, 0).size(PAGE_WIDTH, 178).background("#10243f").z(1)
    background.add_rect().absolute(388, 24).size(170, 92).background("#1d4ed8").opacity(0.16).radius(24).z(2)
    background.add_rect().absolute(34, 118).size(526, 670).background("#ffffff").opacity(0.72).radius(22).z(3)
    page.add(background)

    title_band = Canvas().name("report-title-region").size(523, 92).absolute(36, 70).z(10)
    title_band.add_text("Executive Summary").absolute(0, 0).font_size(28).line_height(34).color("#ffffff").z(2)
    title_band.add_text("Predefined report regions keep dense dashboards predictable while Canvas layers handle background, decoration, and overlays.").absolute(0, 42).font_size(10).line_height(14).color("#cbd5e1").z(2)
    title_band.add_rect().absolute(385, 6).size(138, 54).background("#14b8a6").opacity(0.88).radius(18).z(1)
    title_band.add_text("FY 2026 Q1").absolute(414, 24).font_size(13).line_height(16).color("#ffffff").z(3)
    page.add(title_band)

    add_kpi_card(page, 36, 186, "Revenue", "$4.82M", "+18% vs plan")
    add_kpi_card(page, 218, 186, "Gross Margin", "64.1%", "+3.4 pts QoQ")
    add_kpi_card(page, 400, 186, "Retention", "92%", "Enterprise cohort")

    chart = Canvas().name("chart-placeholder-region").size(340, 220).absolute(36, 294).background("#ffffff").stroke("#dbe3ee", 1).radius(16).z(15)
    chart.add_text("Revenue Trend").absolute(18, 16).font_size(14).line_height(18).color("#0f172a").z(3)
    chart.add_text("Chart placeholder region").absolute(214, 18).font_size(8).line_height(10).color("#94a3b8").z(3)
    chart.add_rect().absolute(18, 54).size(304, 132).background("#f8fafc").stroke("#e2e8f0", 0.8).radius(10).z(1)
    chart.add_line().absolute(42, 150).size(230, 0).stroke("#cbd5e1", 0.6).z(2)
    chart.add_line().absolute(42, 116).size(230, 0).stroke("#cbd5e1", 0.6).z(2)
    chart.add_line().absolute(42, 82).size(230, 0).stroke("#cbd5e1", 0.6).z(2)
    chart.add_rect().absolute(62, 126).size(24, 42).background("#93c5fd").radius(5).z(4)
    chart.add_rect().absolute(112, 104).size(24, 64).background("#60a5fa").radius(5).z(4)
    chart.add_rect().absolute(162, 92).size(24, 76).background("#2563eb").radius(5).z(4)
    chart.add_rect().absolute(212, 72).size(24, 96).background("#0f766e").radius(5).z(4)
    chart.add_text("Q1").absolute(66, 192).font_size(8).line_height(10).color("#64748b").z(4)
    chart.add_text("Q2").absolute(116, 192).font_size(8).line_height(10).color("#64748b").z(4)
    chart.add_text("Q3").absolute(166, 192).font_size(8).line_height(10).color("#64748b").z(4)
    chart.add_text("Q4").absolute(216, 192).font_size(8).line_height(10).color("#64748b").z(4)
    page.add(chart)

    flow_region = Frame().name("flow-content-region").size(164, 220).absolute(395, 294).padding(16).background("#ecfeff").stroke("#99f6e4", 1).radius(16).z(15)
    flow_region.add_text("Flow Content Region").font_size(13).line_height(17).color("#0f172a").margin(bottom=10)
    flow_region.add_text("This fixed-size Frame uses normal flow inside an absolute region, so narrative text can stack without changing neighboring report blocks.").font_size(9).line_height(13).color("#334155").margin(bottom=10)
    flow_region.add_text("- Predefined size\n- Flowing text\n- Independent layer").font_size(9).line_height(13).color("#0f766e")
    page.add(flow_region)

    table_region = Frame().name("table-content-region").size(523, 214).absolute(36, 544).padding(14).background("#ffffff").stroke("#dbe3ee", 1).radius(16).z(15)
    table_region.add_text("Regional Performance").font_size(14).line_height(18).color("#0f172a").margin(bottom=10)
    table_region.add(
        Table([
            ["Region", "Revenue", "Growth", "Operating Note"],
            ["North America", "$1.72M", "+21%", "Expansion in enterprise renewals."],
            ["EMEA", "$1.14M", "+12%", "Stable pipeline with public sector lift."],
            ["APAC", "$1.32M", "+19%", "Partner channel ahead of plan."],
            ["LATAM", "$0.64M", "+9%", "New logos offset currency pressure."],
        ])
        .column_widths([110, 78, 64, "auto"])
        .align(["left", "right", "right", "left"])
        .cell_padding(vertical=7, horizontal=9)
        .header(background="#10243f", color="#ffffff")
        .zebra("#f8fafc")
        .column_style(2, color="#0f766e")
        .font_size(9)
        .line_height(12)
        .color("#1e293b")
        .stroke("#cbd5e1", 0.8)
    )
    page.add(table_region)

    doc.save("examples/v2_11_layered_report.pdf")


if __name__ == "__main__":
    build_report()
