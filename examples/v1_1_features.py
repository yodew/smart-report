"""Generate a PDF showcasing v1.1 report-authoring features."""

from __future__ import annotations

from smart_report import Frame, Image, Table, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    title = frame.add_text("smart-report v1.1 features").font_size(22).line_height(28).margin(bottom=12)
    title.keep_with_next()

    rich_cell = Frame().padding(4).background("#f8fafc")
    rich_cell.add_text("Nested Frame content inside a table cell.").font_size(10).line_height(12)
    rich_cell.add_text("Useful for notes, badges, and multi-part summaries.").font_size(9).line_height(11).color("#475569")

    table = (
        Table([
            ["Metric", "Details", "Value"],
            ["Revenue", rich_cell, "$216K"],
            ["Growth", "Quarter-over-quarter", "+8%"],
        ])
        .column_widths([90, "auto", 80])
        .align(["left", "left", "right"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "", "$216K"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_border(1, 0, color="#2563eb", width=2)
        .cell_padding(vertical=8, horizontal=10)
        .margin(bottom=18)
    )
    frame.add(table)

    image_row = Frame().flex("row", gap=12).keep_together()
    image_row.add(Image("examples/box_middle_crop.png").size(120, 80).cover().radius(8))
    image_row.add(Image("examples/box.png").size(120, 80).contain().radius(8))
    frame.add(image_row)

    frame.add_text("This paragraph starts after the image row.").page_break_after()
    page.add(frame)
    doc.save("examples/v1_1_features.pdf")


if __name__ == "__main__":
    build_report()
