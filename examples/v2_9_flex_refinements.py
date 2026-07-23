"""Generate a PDF showcasing v2.9 flex justify, align, and gap refinements."""

from __future__ import annotations

from smart_report import Frame, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("v2.9 Flex Refinements").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "v2.9 adds justify-content, align-items, and separate row_gap / column_gap "
        "to the flex builder. These give more control over item placement inside "
        "flex containers without changing the underlying layout engine."
    ).font_size(11).line_height(15).margin(bottom=18)

    # ── Justify Content ──────────────────────────────────────────────
    frame.add_text("Justify Content").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "justify controls horizontal placement along the main axis. Supported values: "
        "start, center, end, and space-between."
    ).font_size(11).line_height(15).margin(bottom=8)

    for mode in ("start", "center", "end", "space-between"):
        label = f'justify="{mode}"'
        row = Frame().flex("row", gap=8, justify=mode).width(400).margin(bottom=6)
        row.add_text("A").width(80).padding(8).background("#dbeafe").font_size(10).line_height(13)
        row.add_text("B").width(80).padding(8).background("#dbeafe").font_size(10).line_height(13)
        row.add_text("C").width(80).padding(8).background("#dbeafe").font_size(10).line_height(13)

        wrapper = Frame().flex("row", gap=6).width(400).margin(bottom=6)
        wrapper.add_text(label).width(130).font_size(10).line_height(13)
        wrapper.add(row)
        frame.add(wrapper)

    frame.add_spacer(8)

    # ── Align Items ──────────────────────────────────────────────────
    frame.add_text("Align Items").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "align controls cross-axis placement within a row. When children have "
        "different heights, align offsets shorter items against the tallest one."
    ).font_size(11).line_height(15).margin(bottom=8)

    for mode in ("start", "center", "end"):
        label = f'align="{mode}"'
        row = Frame().flex("row", gap=8, align=mode).width(400).margin(bottom=6)
        row.add_text("Short").padding(8).background("#dcfce7").font_size(10).line_height(13)
        row.add_text("Taller child").padding(16).background("#dcfce7").font_size(10).line_height(13)
        row.add_text("Tiny").padding(4).background("#dcfce7").font_size(10).line_height(13)

        wrapper = Frame().flex("row", gap=6).width(400).margin(bottom=6)
        wrapper.add_text(label).width(130).font_size(10).line_height(13)
        wrapper.add(row)
        frame.add(wrapper)

    frame.add_spacer(8)

    # ── Separate Gaps ────────────────────────────────────────────────
    frame.add_text("Separate Gaps").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "row_gap and column_gap let you set different spacing on each axis. "
        "row_gap controls vertical spacing (between wrapped rows, or between "
        "column children). column_gap controls horizontal spacing (between row "
        "items, or between wrapped-row items). Each falls back to gap when not set."
    ).font_size(11).line_height(15).margin(bottom=8)

    frame.add_text("Row wrap with separate gaps").font_size(12).line_height(16).margin(bottom=4)
    wrapped = Frame().flex("row", gap=8, wrap=True, row_gap=20, column_gap=8).width(300).margin(bottom=12)
    for idx in range(6):
        wrapped.add_text(f"Item {idx + 1}").width(80).padding(8).background("#fef3c7").font_size(
            10
        ).line_height(13)
    frame.add(wrapped)

    frame.add_text(
        "Above: column_gap=8 (horizontal), row_gap=20 (vertical). "
        "Notice the wider vertical spacing between rows compared to the tighter horizontal gaps."
    ).font_size(10).line_height(14).margin(bottom=12)

    frame.add_spacer(8)

    # ── Column Explicit-Height Alignment ─────────────────────────────
    frame.add_text("Column Explicit-Height Alignment").font_size(16).line_height(22).margin(
        bottom=8
    )
    frame.add_text(
        "Column justify distributes space between children vertically, but only when "
        "the parent has an explicit content height. Without a fixed height, justify "
        "is a no-op because there is no remaining space to distribute."
    ).font_size(11).line_height(15).margin(bottom=8)

    col = Frame().flex("column", gap=8, justify="space-between", align="center").width(300).height(
        200
    ).margin(bottom=12)
    col.add_text("Top").padding(8).background("#ede9fe").font_size(10).line_height(13)
    col.add_text("Middle").padding(8).background("#ede9fe").font_size(10).line_height(13)
    col.add_text("Bottom").padding(8).background("#ede9fe").font_size(10).line_height(13)
    frame.add(col)

    frame.add_text(
        "Above: justify=space-between with explicit height=200pt spreads the three "
        "items vertically. align=center centers each item horizontally."
    ).font_size(10).line_height(14).margin(bottom=18)

    frame.add_text("Limitations").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "- This is not full CSS flexbox\n"
        "- No stretch, space-around, or space-evenly\n"
        "- No flex grow, shrink, or basis\n"
        "- No reverse directions\n"
        "- Column wrap is not supported\n"
        "- Wrapped rows stay together across page breaks where practical"
    ).font_size(10).line_height(14)

    page.add(frame)
    doc.save("examples/v2_9_flex_refinements.pdf")


if __name__ == "__main__":
    build_report()
