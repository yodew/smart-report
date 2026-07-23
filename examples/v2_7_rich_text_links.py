"""Generate a PDF showcasing text and RichText URL annotations."""

from __future__ import annotations

from smart_report import Frame, RichText, Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("Text and RichText Links").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Text.link(url) attaches a PDF external URL annotation to a whole text node. "
        "RichText.span(..., link=url) attaches links to inline rich-text spans."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add_text("Linked Text in a Frame").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "This is a plain linked text node. Clicking it opens the smart-report repository."
    ).font_size(11).line_height(15).margin(bottom=4)
    frame.add(
        Text("https://github.com/user/smart-report").link("https://github.com/user/smart-report")
        .font_size(11).line_height(15).color("#2563eb").margin(bottom=12)
    )

    frame.add_text("Inline RichText Links").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "Only linked RichText spans become clickable; adjacent spans remain plain text."
    ).font_size(11).line_height(15).margin(bottom=8)

    link_cell_1 = RichText().span("Documentation", color="#2563eb", underline=True, link="https://example.com/docs").span(" guide")
    link_cell_2 = RichText().span("API", color="#2563eb", underline=True, link="https://example.com/api").span(" reference")
    link_cell_3 = Text("No link here").font_size(10)

    frame.add(
        Table([
            ["Section", "Link"],
            [link_cell_1, "Official documentation site"],
            [link_cell_2, "Full API reference"],
            [link_cell_3, "Plain text cell without a link"],
        ])
        .column_widths([120, "auto"])
        .align(["left", "left"])
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#1d4ed8", color="#ffffff")
        .zebra("#f8fafc")
        .font_size(10)
        .line_height(13)
        .stroke("#cbd5e1", 1)
        .margin((0, 0, 16, 0))
    )

    frame.add_text("Manual Link Styling").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "Links do not get automatic styling. You can opt into color, underline, "
        "or other visual hints using the existing Text and RichText style APIs."
    ).font_size(11).line_height(15).margin(bottom=8)
    frame.add(
        RichText().span("Styled ").span("inline link", color="#2563eb", underline=True, link="https://example.com/styled")
        .font_size(11).line_height(15)
    )

    frame.add_text("Limitations").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "- Text.link(url) applies to the whole Text node\n"
        "- RichText.span(..., link=url) supports inline rich-text links\n"
        "- No markdown or HTML link parsing\n"
        "- No automatic underline or color styling\n"
        "- No plain string table cell link API\n"
        "- No arbitrary PDF annotation API"
    ).font_size(10).line_height(14)

    page.add(frame)
    doc.save("examples/v2_7_rich_text_links.pdf")


if __name__ == "__main__":
    build_report()
