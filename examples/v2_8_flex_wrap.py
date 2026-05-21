"""Generate a PDF showcasing v2.8 flex row wrapping."""

from __future__ import annotations

from smart_report import Frame, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("v2.8 Flex Wrap").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "flex(\"row\", wrap=True) breaks children into multiple rows when "
        "they exceed the container width. The gap value applies both "
        "horizontally between items in a row and vertically between wrapped rows."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add_text("Wrapped Cards").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "Six cards with fixed widths wrap into two rows inside a 480pt container. "
        "Each card is 140pt wide with a 10pt gap between items."
    ).font_size(11).line_height(15).margin(bottom=8)

    cards = Frame().flex("row", gap=10, wrap=True).width(480).margin(bottom=18)
    for index in range(6):
        cards.add_text(f"Card {index + 1}").width(140).padding(10).background(
            "#dbeafe"
        ).color("#1e3a8a").font_size(10).line_height(13)
    frame.add(cards)

    frame.add_text("Gap Behavior").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "The same gap (12pt) separates items horizontally and rows vertically. "
        "Compare with a non-wrapped row to see the difference."
    ).font_size(11).line_height(15).margin(bottom=8)

    non_wrap_row = Frame().flex("row", gap=12).width(480).margin(bottom=12)
    non_wrap_row.add_text("Alpha").width(200).padding(10).background("#f0fdf4").font_size(10).line_height(13)
    non_wrap_row.add_text("Beta").width(200).padding(10).background("#f0fdf4").font_size(10).line_height(13)
    frame.add(non_wrap_row)

    wrapped_row = Frame().flex("row", gap=12, wrap=True).width(280).margin(bottom=18)
    wrapped_row.add_text("Alpha").width(200).padding(10).background("#fef3c7").font_size(10).line_height(13)
    wrapped_row.add_text("Beta").width(200).padding(10).background("#fef3c7").font_size(10).line_height(13)
    frame.add(wrapped_row)

    frame.add_text("Explicit Child Widths").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "When children have explicit widths, the wrap algorithm uses those widths "
        "to decide when to start a new row. No auto-shrinking or stretching occurs."
    ).font_size(11).line_height(15).margin(bottom=8)

    explicit = Frame().flex("row", gap=8, wrap=True).width(360).margin(bottom=18)
    explicit.add_text("80pt").width(80).padding(8).background("#ede9fe").font_size(10).line_height(13)
    explicit.add_text("120pt").width(120).padding(8).background("#ede9fe").font_size(10).line_height(13)
    explicit.add_text("80pt").width(80).padding(8).background("#ede9fe").font_size(10).line_height(13)
    explicit.add_text("120pt").width(120).padding(8).background("#ede9fe").font_size(10).line_height(13)
    frame.add(explicit)

    frame.add_text("Auto Text Fallback").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "Text children without explicit widths measure to their natural text width. "
        "Short labels stay compact; longer labels take more space."
    ).font_size(11).line_height(15).margin(bottom=8)

    auto_text = Frame().flex("row", gap=10, wrap=True).width(400).margin(bottom=18)
    auto_text.add_text("Short").padding(8).background("#ecfeff").font_size(10).line_height(13)
    auto_text.add_text("Medium label").padding(8).background("#ecfeff").font_size(10).line_height(13)
    auto_text.add_text("A much longer label here").padding(8).background("#ecfeff").font_size(10).line_height(13)
    auto_text.add_text("Tiny").padding(8).background("#ecfeff").font_size(10).line_height(13)
    frame.add(auto_text)

    frame.add_text("Oversized Item").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "A single child wider than the container is placed alone on its row. "
        "It may overflow horizontally beyond the container edge."
    ).font_size(11).line_height(15).margin(bottom=8)

    oversized_row = Frame().flex("row", gap=10, wrap=True).width(300).margin(bottom=12)
    oversized_row.add_text("Wide").width(200).padding(10).background("#fee2e2").font_size(10).line_height(13)
    oversized_row.add_text("Oversized Item").width(400).padding(10).background("#fee2e2").font_size(10).line_height(13)
    frame.add(oversized_row)

    frame.add_text("Limitations").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "- Row-only wrapping; column wrap is not supported\n"
        "- No justify-content or align-items APIs\n"
        "- No row_gap / column_gap separation; a single gap applies to both axes\n"
        "- Not a full CSS flexbox implementation\n"
        "- No row-aware pagination guarantee across page breaks"
    ).font_size(10).line_height(14)

    page.add(frame)
    doc.save("examples/v2_8_flex_wrap.pdf")


if __name__ == "__main__":
    build_report()
