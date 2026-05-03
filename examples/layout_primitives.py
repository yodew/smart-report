"""Flex, grid, columns, and deeper pagination demo."""

from smart_report import Frame, document


def main() -> None:
    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(32)
    frame.add_text("Layout primitives demo").font_size(20).margin(bottom=16)

    flex_row = Frame().flex("row", gap=12).margin(bottom=18)
    for label in ("Summary", "Revenue", "Growth"):
        flex_row.add_text(label).padding(10).background("#dbeafe").color("#1e3a8a")
    frame.add(flex_row)

    grid = Frame().grid(3, gap=10).margin(bottom=18)
    for index in range(6):
        grid.add_text(f"Grid card {index + 1}").padding(10).background("#f8fafc").stroke("#cbd5e1", 1)
    frame.add(grid)

    columns = Frame().columns(2, gap=16).margin(bottom=18)
    for index in range(8):
        columns.add_text(f"Column item {index + 1}: content flows into the shortest column.").padding(8).background("#ecfeff")
    frame.add(columns)

    frame.add_text("The large block below is split as fixed-height fragments during pagination.").margin(bottom=8)
    frame.add_rect().height(900).background("#fee2e2").stroke("#fca5a5", 1)

    page.add(frame)
    doc.save("examples/layout_primitives.pdf")


if __name__ == "__main__":
    main()
