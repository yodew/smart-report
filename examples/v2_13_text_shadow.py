"""Demonstrate block-level Text and RichText shadows."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image as PillowImage

from smart_report import Canvas, Frame, RichText, document


OUTPUT = Path(__file__).with_name("v2_13_text_shadow.pdf")


def _image_data_url() -> str:
    image = PillowImage.new("RGB", (480, 180), "#16355f")
    for y in range(image.height):
        for x in range(image.width):
            blue = 72 + int(80 * x / image.width)
            green = 52 + int(64 * y / image.height)
            image.putpixel((x, y), (18, green, blue))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def main() -> None:
    doc = document()
    page = doc.page("A4")

    hero = Canvas().height(188).background("#0f172a").background_image(_image_data_url(), fit="cover", opacity=0.88)
    hero.add_text("Block-level Text shadow") \
        .absolute(32, 42) \
        .width(420) \
        .font_size(30) \
        .line_height(36) \
        .color("#ffffff") \
        .text_shadow(x=0, y=0, blur=4, spread=0, color="#FFFFFF")
    hero.add_text("Vector outline approximation: stroked PDF text, not raster blur.") \
        .absolute(34, 94) \
        .width(420) \
        .font_size(11) \
        .line_height(15) \
        .color("#dbeafe") \
        .text_shadow(x=1, y=1, blur=2, color="#00000080")
    page.add(hero)

    content = Frame().padding(vertical=28, horizontal=32).background("#f8fafc")
    card = Canvas().height(150).background("#111827").radius(18).padding(0)
    card.add_rect().absolute(18, 18).size(110, 110).background("#2563eb").radius(24)
    rich = RichText() \
        .span("RichText ", font_size=24, color="#ffffff") \
        .span("shadow", font_size=24, color="#fde68a", bold=True) \
        .br() \
        .span("applies to the whole rich text block", font_size=12, color="#cbd5e1") \
        .text_shadow(x=0, y=0, blur=2.5, spread=0, color="rgba(255, 255, 255, 0.22)") \
        .width(330)
    card.add(rich).absolute(154, 42)
    content.add(card)
    page.add(content)

    doc.save(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
