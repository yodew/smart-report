"""Generate a PDF showcasing v2.1 mixed rich-row pagination and flex column gaps."""

from __future__ import annotations

from smart_report import Frame, Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    frame.add_text("smart-report v2.1 features").font_size(22).line_height(28).margin(bottom=12).keep_with_next()
    frame.add_text("Mixed rich Text + Frame table rows can split, while rich Image cells remain atomic.").font_size(11).line_height(15).margin(bottom=14)

    stack = Frame().flex("column", gap=8).background("#f8fafc").padding(8).margin(bottom=16)
    stack.add_text("Column flex item one").font_size(10).line_height(12)
    stack.add_text("Column flex item two after an 8pt gap").font_size(10).line_height(12)
    frame.add(stack)

    notes = Text(" ".join(f"Text note {index}: long-form operational detail." for index in range(1, 70))).font_size(9).line_height(12)
    detail = Frame().padding(4).background("#eef2ff")
    for index in range(1, 18):
        detail.add_text(f"Frame detail {index}: nested rich content in the same row.").font_size(9).line_height(12).margin(bottom=2)

    table = (
        Table([
            ["Metric", "Text Details", "Frame Details"],
            ["Retention", notes, detail],
        ])
        .column_widths([80, "auto", "auto"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "Reviewed", "Tracked"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_padding(vertical=8, horizontal=10)
    )
    frame.add(table)

    doc.save("examples/v2_1_features.pdf")


if __name__ == "__main__":
    build_report()
