"""Pagination + overlay example for smart-report."""

from smart_report import Frame, Table, document


def main() -> None:
    doc = document()

    header = doc.header().height(40)
    header.add_text("smart-report v1.1 demo").absolute(24, 12).font_size(11).color("#334155")
    header.add_text("Page {page_number} / {total_pages}").absolute("78%", 12).font_size(11).color("#334155")

    footer = doc.footer().height(32)
    footer.add_text("Confidential").absolute(24, 8).font_size(10).color("#64748b")

    watermark = doc.watermark().height(200).opacity(0.08)
    watermark.add_text("DRAFT").absolute(170, 280).font_size(72).color("#94a3b8")

    page = doc.page("A4")
    frame = Frame().padding(36)

    for index in range(35):
        frame.add_text(
            f"Section {index + 1}: "
            + "This paragraph is intentionally repeated to trigger automatic pagination. " * 3
        ).font_size(12).color("#1e293b").margin((0, 0, 12, 0))

    rows = [["Region", "Revenue", "Growth"]]
    for index in range(28):
        rows.append([f"Region {index + 1}", f"${(index + 1) * 125}K", f"+{(index % 9) + 3}%"])

    frame.add(
        Table(rows)
        .column_widths(["45%", "30%", "25%"])
        .align(["left", "right", "right"])
        .cell_padding(vertical=7, horizontal=9)
        .header(background="#0f172a", color="#ffffff", repeat=True)
        .zebra("#f8fafc")
        .font_size(10)
        .line_height(13)
        .color("#111827")
        .background("#ffffff")
        .stroke("#cbd5e1", 1)
        .margin((12, 0, 0, 0))
    )
    page.add(frame)

    doc.save("examples/paginated_report.pdf")


if __name__ == "__main__":
    main()
