"""Generate a PDF showcasing v2.7 rich text links: whole-Text URL annotations."""

from __future__ import annotations

from smart_report import Frame, Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("v2.7 Rich Text Links").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Text.link(url) attaches a PDF external URL annotation to the whole text node. "
        "Clicking anywhere on the text opens the link in a browser."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add_text("Linked Text in a Frame").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "This is a plain linked text node. Clicking it opens the smart-report repository."
    ).font_size(11).line_height(15).margin(bottom=4)
    frame.add(
        Text("https://github.com/user/smart-report").link("https://github.com/user/smart-report")
        .font_size(11).line_height(15).color("#2563eb").margin(bottom=12)
    )

    frame.add_text("Linked Rich Text Table Cells").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "Rich Text nodes used as table cells can carry links. "
        "The entire cell text becomes the clickable area."
    ).font_size(11).line_height(15).margin(bottom=8)

    link_cell_1 = Text("Documentation").link("https://example.com/docs")
    link_cell_2 = Text("API Reference").link("https://example.com/api")
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
        "Links do not get automatic styling. You can opt into color or other "
        "visual hints using the existing Text style APIs."
    ).font_size(11).line_height(15).margin(bottom=8)
    frame.add(
        Text("Styled link text").link("https://example.com/styled")
        .font_size(11).line_height(15).color("#2563eb")
    )

    frame.add_text("Limitations").font_size(16).line_height(22).margin(bottom=8)
    frame.add_text(
        "- Whole-Text links only; no inline substring links\n"
        "- No markdown or HTML link parsing\n"
        "- No automatic underline or color styling\n"
        "- No plain string table cell link API\n"
        "- No arbitrary PDF annotation API"
    ).font_size(10).line_height(14)

    page.add(frame)
    doc.save("examples/v2_7_rich_text_links.pdf")


if __name__ == "__main__":
    build_report()
