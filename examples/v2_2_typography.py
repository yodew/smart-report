"""Generate a PDF showcasing v2.2 typography preprocessing."""

from __future__ import annotations

from pathlib import Path

from smart_report import Table, document, register_font
from smart_report.style.typography import shape_text

FONT_DIR = Path(__file__).with_name("fonts")
ARABIC_MEDIUM = "NotoNaskhArabic-Medium"
ARABIC_BOLD = "NotoNaskhArabic-Bold"
SYMBOLS_MEDIUM = "NotoSansSymbols-Medium"


def register_demo_fonts() -> None:
    register_font(ARABIC_MEDIUM, FONT_DIR / "NotoNaskhArabic-Medium.ttf", fallback=True)
    register_font(ARABIC_BOLD, FONT_DIR / "NotoNaskhArabic-Bold.ttf")
    register_font(SYMBOLS_MEDIUM, FONT_DIR / "NotoSansSymbols-Medium.ttf", fallback=True)


def build_report() -> None:
    register_demo_fonts()

    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    frame.add_text("smart-report v2.2 typography").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Typography auto mode reshapes Arabic-script text and applies bidi display ordering before measurement, pagination, and painting."
    ).font_size(11).line_height(15).margin(bottom=14)

    rtl_text = "مرحبا smart-report"
    frame.add_text("Raw logical text:").font_size(10).line_height(12).margin(bottom=4)
    frame.add_text(rtl_text).font(ARABIC_MEDIUM).font_size(14).line_height(18).margin(bottom=10)

    frame.add_text("Preprocessed display text:").font_size(10).line_height(12).margin(bottom=4)
    frame.add_text(shape_text(rtl_text, "auto", "rtl")).font(ARABIC_MEDIUM).font_size(14).line_height(18).margin(bottom=10)

    frame.add_text("Text node with typography('auto').text_direction('rtl'):").font_size(10).line_height(12).margin(bottom=4)
    frame.add_text(rtl_text).font(ARABIC_MEDIUM).typography("auto").text_direction("rtl").font_size(14).line_height(18).margin(bottom=16)

    table = (
        Table([
            ["Field", "Value"],
            ["Logical", rtl_text],
            ["Table auto", rtl_text],
        ])
        .column_widths([90, "auto"])
        .header(background="#1d4ed8", color="#ffffff")
        .cell_padding(vertical=8, horizontal=10)
        .font(ARABIC_MEDIUM)
        .header_style(font=ARABIC_BOLD)
        .typography("auto")
        .text_direction("rtl")
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
    )
    frame.add(table)

    doc.save("examples/v2_2_typography.pdf")


if __name__ == "__main__":
    build_report()
