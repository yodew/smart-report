"""Generate a PDF showcasing v2.0 layout stabilization."""

from __future__ import annotations

from smart_report import Frame, Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    frame.add_text("smart-report v2.0 features").font_size(22).line_height(28).margin(bottom=12).keep_with_next()
    frame.add_text("Percentage absolute top values now resolve against final auto-height content.").font_size(11).line_height(15).margin(bottom=14)

    panel = Frame().padding(12).background("#f8fafc").margin(bottom=18)
    panel.add_text("Auto-height panel with flow content.").font_size(11).line_height(15)
    panel.add_text("50% badge").absolute(0, "50%").background("#dbeafe").padding(vertical=3, horizontal=6).font_size(9).line_height(11)
    frame.add(panel)

    left = Text(" ".join(f"Left note {index}." for index in range(1, 70))).font_size(9).line_height(12)
    right = Text(" ".join(f"Right note {index}." for index in range(1, 70))).font_size(9).line_height(12)
    table = (
        Table([
            ["Metric", "Operations", "Risks"],
            ["Retention", left, right],
        ])
        .column_widths([80, "auto", "auto"])
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .footer([["Total", "Reviewed", "Tracked"]], repeat=True, background="#e2e8f0")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
        .cell_padding(vertical=8, horizontal=10)
    )
    frame.add(table)

    doc.save("examples/v2_0_features.pdf")


if __name__ == "__main__":
    build_report()
