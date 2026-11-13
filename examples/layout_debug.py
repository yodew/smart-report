"""Run with .venv/bin/python examples/layout_debug.py to inspect layout boxes."""

# /// script
# requires-python = ">=3.10"
# dependencies = ["smart-report"]
# ///

from __future__ import annotations

from smart_report import Canvas, document


def main() -> None:
    doc = document()
    page = doc.page((300, 240)).padding(20)
    card = Canvas().size(240, 120).padding(12).overflow("hidden").name("summary-card")
    card.background("#eff6ff")
    card.add_text("Layout diagnostics").font_size(18).width(210).name("title")
    card.add_text("Blue: node bounds\nGreen: content area\nOrange: clip region").absolute(12, 40).width(210).font_size(11).name("legend")
    page.add(card)
    page.add_rect().absolute(220, 165).size(80, 40).background("#fed7aa").name("outside-page")
    doc.save("examples/layout_debug.pdf", debug_layout=True)


if __name__ == "__main__":
    main()
