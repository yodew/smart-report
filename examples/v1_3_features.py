"""Generate a PDF showcasing v1.3 rich Text table-cell pagination."""

from __future__ import annotations

from smart_report import Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    frame.add_text("smart-report v1.3 features").font_size(22).line_height(28).margin(bottom=12).keep_with_next()
    frame.add_text("A rich Text object inside a regular table cell can now split across pages.").font_size(11).line_height(15).margin(bottom=14)

    details = Text(" ".join(f"Text-rich-cell note {index}: operational detail for the report." for index in range(1, 95))).font_size(9).line_height(12)

    table = (
        Table([
            ["Metric", "Details", "Value"],
            ["Retention", details, "94%"],
            ["Expansion", "Existing Frame rich cells still split as in v1.2.", "+11%"],
        ])
        .column_widths([90, "auto", 70])
        .align(["left", "left", "right"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "", "105%"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_padding(vertical=8, horizontal=10)
    )
    frame.add(table)

    doc.save("examples/v1_3_features.pdf")


if __name__ == "__main__":
    build_report()
