"""Generate a PDF showcasing v1.5 multi-rich Text table-cell pagination."""

from __future__ import annotations

from smart_report import Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    frame.add_text("smart-report v1.5 features").font_size(22).line_height(28).margin(bottom=12).keep_with_next()
    frame.add_text("Rows with multiple rich Text cells can now split across pages when they are not spanned.").font_size(11).line_height(15).margin(bottom=14)

    notes = Text(" ".join(f"Operations note {index}: long-form text for the left rich cell." for index in range(1, 80))).font_size(9).line_height(12)
    risks = Text(" ".join(f"Risk note {index}: long-form text for the right rich cell." for index in range(1, 80))).font_size(9).line_height(12)

    table = (
        Table([
            ["Metric", "Operations", "Risks"],
            ["Retention", notes, risks],
            ["Expansion", "Plain text rows still paginate normally.", "Images and mixed rich rows remain atomic."],
        ])
        .column_widths([80, "auto", "auto"])
        .align(["left", "left", "left"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "Reviewed", "Tracked"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_padding(vertical=8, horizontal=10)
    )
    frame.add(table)

    doc.save("examples/v1_5_features.pdf")


if __name__ == "__main__":
    build_report()
