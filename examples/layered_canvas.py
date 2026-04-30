"""Layered canvas example for smart-report."""

from smart_report import Canvas, document


def main() -> None:
    doc = document()
    page = doc.page("A4")

    canvas = Canvas().height(220).margin(vertical=32, horizontal=32).background("#f8fafc").stroke("#cbd5e1", 1)
    canvas.add_rect().absolute(0, 0).size("100%", 220).background("#dbeafe").z(0)
    canvas.add_rect().absolute(24, 110).size(240, 64).background("#1d4ed8").radius(14).z(1)
    canvas.add_text("Layered Canvas Demo").absolute(24, 24).font_size(26).color("#1e3a8a").z(2)
    canvas.add_text("Text and shapes overlap using z-index sorting before paint.").absolute(24, 72).font_size(12).color("#334155").z(2)
    canvas.add_text("z=1 card block").absolute(40, 130).font_size(16).color("#ffffff").z(3)

    page.add(canvas)
    doc.save("examples/layered_canvas.pdf")


if __name__ == "__main__":
    main()
