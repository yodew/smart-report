"""Generate a PDF showcasing v1.2 rich table-cell pagination."""

from __future__ import annotations

from smart_report import Frame, Table, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("smart-report v1.2 features").font_size(22).line_height(28).margin(bottom=12).keep_with_next()
    frame.add_text("A rich Frame inside a regular table cell can now split across pages while repeating headers.").font_size(11).line_height(15).margin(bottom=14)

    details = Frame().padding(4).background("#f8fafc")
    for index in range(1, 70):
        details.add_text(f"Nested rich-cell paragraph {index}: detailed operational note for the report.").font_size(9).line_height(12).margin(bottom=3)

    table = (
        Table([
            ["Metric", "Details", "Value"],
            ["Revenue", details, "$216K"],
            ["Growth", "Quarter-over-quarter", "+8%"],
        ])
        .column_widths([90, "auto", 80])
        .align(["left", "left", "right"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "", "$216K"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_padding(vertical=8, horizontal=10)
    )
    frame.add(table)
    page.add(frame)

    doc.save("examples/v1_2_features.pdf")


if __name__ == "__main__":
    build_report()
