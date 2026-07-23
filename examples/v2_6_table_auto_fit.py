"""Generate a PDF showcasing v2.6 table auto-fit columns."""

from __future__ import annotations

from smart_report import Frame, RichText, Table, Text, document


def build_report() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(36)

    frame.add_text("Auto-fit Columns").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "When no explicit column_widths are set, auto_fit_columns() sizes every "
        "column to its natural text width plus cell padding."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add(
        Table([
            ["Region", "Revenue", "Growth"],
            ["APAC", "$1.20M", "+18%"],
            ["EMEA", "$0.98M", "+11%"],
            ["North America", "$1.60M", "+23%"],
        ])
        .auto_fit_columns()
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#1d4ed8", color="#ffffff")
        .zebra("#f8fafc")
        .font_size(10)
        .line_height(13)
        .stroke("#cbd5e1", 1)
        .margin((0, 0, 16, 0))
    )

    frame.add_text("Selected-Column Auto-fit").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Passing column indexes to auto_fit_columns() sizes only those columns. "
        "The remaining columns keep their explicit widths."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add(
        Table([
            ["ID", "Product", "Category", "Revenue"],
            ["1001", "Widget Alpha", "Widgets", "$450"],
            ["1002", "Widget Beta", "Widgets", "$380"],
            ["2001", "Gadget Pro", "Gadgets", "$1,200"],
            ["2002", "Gadget Lite", "Gadgets", "$720"],
        ])
        .column_widths([60, "auto", "auto", 80])
        .auto_fit_columns([1, 2])
        .align(["left", "left", "left", "right"])
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#0f172a", color="#ffffff")
        .zebra("#f8fafc")
        .font_size(10)
        .line_height(13)
        .stroke("#cbd5e1", 1)
        .margin((0, 0, 16, 0))
    )

    frame.add_text("Fit Then Clamp").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Auto-fit widths respect column_min_widths and column_max_widths. Columns "
        "are first sized to natural width, then clamped to the configured bounds."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add(
        Table([
            ["Code", "Description", "Status"],
            ["A", "A very short label", "Active"],
            ["BB", "A much longer description that would normally be quite wide", "Pending"],
            ["CCC", "Medium text", "Closed"],
        ])
        .auto_fit_columns()
        .column_min_widths([60, 160, 80])
        .column_max_widths([120, 350, 150])
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#059669", color="#ffffff")
        .zebra("#f0fdf4")
        .font_size(10)
        .line_height(13)
        .stroke("#94a3b8", 1)
        .margin((0, 0, 16, 0))
    )

    frame.add_text('Legacy column_widths(["auto"])').font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        'Without auto_fit_columns(), "auto" in column_widths still means '
        "equal-share distribution across auto columns, preserving backward compatibility."
    ).font_size(11).line_height(15).margin(bottom=12)

    frame.add(
        Table([
            ["Item", "Price", "Qty"],
            ["Widget", "$10", "5"],
            ["Gadget", "$25", "2"],
        ])
        .column_widths(["auto", "auto", "auto"])
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#7c3aed", color="#ffffff")
        .zebra("#faf5ff")
        .font_size(10)
        .line_height(13)
        .stroke("#cbd5e1", 1)
        .margin((0, 0, 16, 0))
    )

    frame.add_text("Rich-Cell Auto-fit").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Auto-fit also measures supported rich Text, RichText, and simple flow Frame cells. "
        "Complex rich cells such as images or absolute/flex layouts remain conservative."
    ).font_size(11).line_height(15).margin(bottom=12)

    rich_note = RichText().span("Enterprise ").span("renewals", bold=True, underline=True).br().span("remained strong", italic=True)
    frame_cell = Frame().padding(vertical=2, horizontal=4)
    frame_cell.add_text("Framed total").font_size(10)

    frame.add(
        Table([
            ["Region", "Revenue", "Note"],
            [Text("North America premium plans"), "$1.60M", rich_note],
            [frame_cell, "$3.78M", "Grand Total"],
        ])
        .auto_fit_columns()
        .cell_padding(vertical=7, horizontal=10)
        .header(background="#1d4ed8", color="#ffffff")
        .zebra("#f8fafc")
        .row_style(2, background="#e2e8f0")
        .font_size(10)
        .line_height(13)
        .stroke("#94a3b8", 1)
    )

    page.add(frame)
    doc.save("examples/v2_6_table_auto_fit.pdf")


if __name__ == "__main__":
    build_report()
