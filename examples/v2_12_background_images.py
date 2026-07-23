"""Demonstrate v2.12 background images for containers and tables."""

from __future__ import annotations

from pathlib import Path

from smart_report import document
from smart_report.containers.canvas import Canvas
from smart_report.containers.frame import Frame
from smart_report.containers.table import Table


PAGE_WIDTH = 595.2756


def main() -> None:
    output = Path(__file__).with_name("v2_12_background_images.pdf")
    hero_image = Path(__file__).with_name("cover.jpg")

    doc = document()
    page = doc.page("A4")

    hero = (
        Canvas()
        .height(190)
        .margin(top=28, right=32, bottom=24, left=32)
        .background("#0f172a")
        .background_image(hero_image, fit="cover", opacity=0.42)
        .stroke("#1e293b", 1)
        .radius(22)
    )
    hero.add_text("Background image cards").absolute(24, 28).font_size(26).line_height(32).color("#ffffff").z(2)
    hero.add_text("Canvas and Frame can use paths, bytes, or data URLs as background images.").absolute(24, 72).width(PAGE_WIDTH - 112).font_size(11).line_height(15).color("#dbeafe").z(2)
    page.add(hero)

    card = (
        Frame()
        .padding(vertical=16, horizontal=18)
        .margin(right=32, bottom=22, left=32)
        .background("#ffffff")
        .background_image(hero_image, fit="cover", opacity=0.08)
        .stroke("#dbe3ee", 1)
        .radius(18)
    )
    card.add_text("A practical title card").font_size(18).line_height(24).color("#0f172a").margin(bottom=8)
    card.add_text("The image layer sits below text and borders, so it works as a subtle visual texture without changing content layout.").font_size(11).line_height(15).color("#475569")
    page.add(card)

    table = (
        Table([
            ["Region", "Revenue", "Growth"],
            ["APAC", "$1.20M", "+18%"],
            ["EMEA", "$0.98M", "+11%"],
            ["AMER", "$1.42M", "+15%"],
        ])
        .column_widths([160, 140, 120])
        .cell_padding(vertical=10, horizontal=12)
        .header(background="rgba(15,23,42,0.92)", color="#ffffff")
        .zebra("rgba(248,250,252,0.84)")
        .background_image(hero_image, fit="cover", opacity=0.10)
        .borders("#cbd5e1", width=0.8)
        .radius(14)
        .margin(right=32, left=32)
    )
    page.add(table)

    doc.save(str(output))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
