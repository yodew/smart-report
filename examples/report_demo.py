"""Enterprise-style report example for smart-report."""

from smart_report import Canvas, Frame, RichText, Table, document


def main() -> None:
    doc = document()
    page = doc.page("A4")

    hero = Canvas().height(300).margin(top=24, right=24, bottom=20, left=24).background("#eff6ff").stroke("#bfdbfe", 1)
    hero.add_rect().absolute(0, 0).size("100%", 180).background("#dbeafe").z(0)
    hero.add_text("Quarterly Revenue Report").absolute(24, 24).font_size(26).color("#1d4ed8").z(2)
    hero.add_text("A layered PDF composition example built on top of ReportLab canvas.").absolute(24, 66).font_size(12).color("#334155").z(2)
    hero.add_rect("Growth +18% YoY").absolute(24, 110).padding(vertical=8, horizontal=14).background("#1d4ed8").color("#ffffff").font_size(14).radius(12).z(1)
    hero.add_text("PNG image").absolute(24, 198).font_size(10).color("#475569").z(3)
    hero.add_text("SVG image").absolute(286, 198).font_size(10).color("#475569").z(3)
    hero.add_rect().absolute(24, 218).size(260, 37).background("#050505").radius(18).z(2)
    hero.add_rect().absolute(286, 218).size(260, 37).background("#050505").radius(18).z(2)
    hero.add_image("examples/box.png").absolute(24, 218).size(260, 37).z(3)
    hero.add_image("examples/box.svg").absolute(286, 218).size(260, 37).z(3)
    page.add(hero)

    content = Frame().padding(24)
    content.add_text("Executive Summary").font_size(20).color("#0f172a").margin(bottom=16)
    content.add_text(
        "smart-report combines top-down width resolution, bottom-up measurement, "
        "and z-index aware paint ordering so report-like layouts can mix flow content with layered composition."
    ).font_size(12).color("#334155").margin(bottom=20)
    rich_note = (
        RichText()
        .font_size(11)
        .span("RichText spans can be ", color="#334155")
        .span("italic", italic=True, color="#0f172a")
        .span(" and ", color="#334155")
        .span("underlined", italic=True, underline=True, color="#0f766e")
        .span(" inline.", color="#334155")
        .margin(bottom=18)
    )
    content.add(rich_note)
    content.add(Table([
        ["Region", "Revenue", "Growth", "Notes"],
        ["APAC", "$1.20M", "+18%", "Strong partner demand and renewed enterprise contracts."],
        ["EMEA", "$0.98M", "+11%", "Stable pipeline with moderate expansion in public sector accounts."],
        ["North America", "$1.60M", "+23%", "Best performing region with premium plan adoption."],
    ])
        .column_widths([110, 90, 70, "auto"])
        .align(["left", "right", "right", "left"])
        .cell_padding(vertical=8, horizontal=10)
        .header(background="#1d4ed8", color="#ffffff")
        .zebra("#f8fafc")
        .row_style(2, background="#ecfeff")
        .column_style(2, color="#065f46")
        .cell_style(3, 1, background="#dcfce7", color="#166534", align="right")
        .font_size(11)
        .line_height(14)
        .color("#111827")
        .background("#ffffff")
        .stroke("#94a3b8", 1)
    )

    page.add(content)
    doc.save("examples/report_demo.pdf")


if __name__ == "__main__":
    main()
