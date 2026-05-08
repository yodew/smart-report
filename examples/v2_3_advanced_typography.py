"""Generate a PDF showcasing v2.3 font families and advanced typography."""

from __future__ import annotations

from pathlib import Path

from smart_report import Frame, Table, document, register_font, register_font_family, shaped_string_width, string_width

FONT_DIR = Path(__file__).with_name("fonts")
ARABIC_FAMILY = "NotoNaskhArabic"
CHINESE_FONT = "SourceHanSansSC-Normal"


def register_demo_fonts() -> None:
    register_font_family(
        ARABIC_FAMILY,
        regular=FONT_DIR / "NotoNaskhArabic-Medium.ttf",
        bold=FONT_DIR / "NotoNaskhArabic-Bold.ttf",
        fallback=True,
    )
    register_font(CHINESE_FONT, FONT_DIR / "SourceHanSansSC-Normal.ttf", fallback=True)


def build_report() -> None:
    register_demo_fonts()

    doc = document()
    page = doc.page("A4")
    frame = page.add_frame().padding(36)

    arabic = "مرحبا smart-report"
    raw_width = string_width(arabic, ARABIC_FAMILY, 16)
    shaped_width = shaped_string_width(arabic, ARABIC_FAMILY, 16)

    frame.add_text("smart-report v2.3 advanced typography").font_size(22).line_height(28).margin(bottom=12)
    frame.add_text(
        "Font families can register regular/bold faces. Advanced typography uses HarfBuzz metrics for shaping-aware measurement while keeping ReportLab text rendering."
    ).font_size(11).line_height(15).margin(bottom=14)

    panel = Frame().padding(10).background("#f8fafc").margin(bottom=16)
    panel.add_text(arabic).font_family(ARABIC_FAMILY).typography("advanced").text_direction("rtl").font_size(16).line_height(22)
    panel.add_text(f"ReportLab width: {raw_width:.2f} pt").font_size(9).line_height(12)
    panel.add_text(f"HarfBuzz width: {shaped_width:.2f} pt").font_size(9).line_height(12)
    frame.add(panel)

    table = (
        Table([
            ["Script", "Sample", "Mode"],
            ["Arabic", arabic, "advanced + rtl"],
            ["Mixed", "مرحبا + Revenue + 中文", "fallback fonts"],
        ])
        .column_widths([80, "auto", 110])
        .header(background="#1d4ed8", color="#ffffff")
        .header_style(font=f"{ARABIC_FAMILY}-Bold")
        .font_family(ARABIC_FAMILY)
        .typography("advanced")
        .text_direction("rtl")
        .cell_padding(vertical=8, horizontal=10)
        .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
    )
    frame.add(table)

    doc.save("examples/v2_3_advanced_typography.pdf")


if __name__ == "__main__":
    build_report()
