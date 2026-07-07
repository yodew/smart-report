"""Focused v2.11 example: page image layer, table region, centered table."""

from __future__ import annotations

from pathlib import Path

from smart_report import Canvas, Table, document


PAGE_WIDTH = 595.2756
PAGE_HEIGHT = 841.8898

REGION_WIDTH = 430
REGION_HEIGHT = 150
REGION_LEFT = (PAGE_WIDTH - REGION_WIDTH) / 2
REGION_TOP = 560

TABLE_WIDTH = 340
TABLE_HEIGHT = 106
TABLE_LEFT = (REGION_WIDTH - TABLE_WIDTH) / 2
TABLE_TOP = (REGION_HEIGHT - TABLE_HEIGHT) / 2

EXAMPLE_DIR = Path(__file__).resolve().parent
BACKGROUND_IMAGE = EXAMPLE_DIR / "cover.jpg"
OUTPUT_PDF = EXAMPLE_DIR / "v2_11_layered_table_region.pdf"


def build_report() -> None:
    doc = document()
    page = doc.page("A4")

    page_background = Canvas().name("current-page-background-image").size(PAGE_WIDTH, PAGE_HEIGHT).absolute(0, 0).z(-30)
    page_background.add_image(str(BACKGROUND_IMAGE)).absolute(0, 0).size(PAGE_WIDTH, PAGE_HEIGHT).cover().z(0)
    page.add(page_background)

    table_region = (
        Canvas()
        .name("visible-table-background-region")
        .size(REGION_WIDTH, REGION_HEIGHT)
        .absolute(REGION_LEFT, REGION_TOP)
        .radius(18)
        .z(10)
    )
    table_region.add_rect().absolute(0, 0).size(REGION_WIDTH, REGION_HEIGHT).background("transparent").stroke("rgba(148,163,184,0.45)", 0.8).radius(18).z(0)
    table_region.add(
        Table([
            ["项目", "结果", "建议"],
            ["体质洞察", "平稳", "保持作息"],
            ["身心平衡", "良好", "适度运动"],
            ["科学调养", "提升", "清淡饮食"],
        ])
        .absolute(TABLE_LEFT, TABLE_TOP)
        .column_widths([110, 90, 140])
        .align(["left", "center", "left"])
        .cell_padding(vertical=7, horizontal=10)
        .header(background="transparent", color="#123766")
        .zebra("transparent")
        .column_style(2, color="#1f4b7a")
        .font_size(10)
        .line_height(12)
        .color("#1e3a5f")
        .z(3)
    )
    page.add(table_region)

    doc.save(str(OUTPUT_PDF))


if __name__ == "__main__":
    build_report()
