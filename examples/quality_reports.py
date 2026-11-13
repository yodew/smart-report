"""Small fixed reports used for content and visual regression checks."""

from __future__ import annotations

from pathlib import Path

from smart_report import DocumentBuilder, Frame, RichText, Table, document, register_font

FONT_PATH = Path(__file__).resolve().parent / "fonts/SourceHanSansSC-Normal.ttf"
FONT_NAME = "QualityReportSans"


def chinese_report() -> DocumentBuilder:
    """Exercise CJK wrapping, first-line indents, pagination and page overlays."""
    register_font(FONT_NAME, FONT_PATH)
    doc = document()
    doc.header().height(28).add_text("中文报告回归样本").absolute(24, 8).width(232).font(FONT_NAME).font_size(9)
    doc.footer().height(20).add_text("Page {page_number}/{total_pages}").absolute(24, 4).width(232).font_size(8)
    frame = Frame().padding(8)
    doc.page((280, 240)).padding(24).add(frame)
    for index in range(8):
        frame.add_text(
            f"段落{index + 1:02d}：中文报告需要稳定的自动换行、首行缩进和跨页布局。"
            "内容增长时，页眉页脚不应覆盖正文，文本也不应丢失或重复。"
        ).font(FONT_NAME).font_size(11).line_height(16).text_indent("2em").margin(bottom=8)
    return doc


def rich_table_report() -> DocumentBuilder:
    """Exercise long rich cells, repeated headers, source-row styles and links."""
    doc = document()
    frame = Frame()
    doc.page((300, 240)).padding(20).add(frame)
    rows: list[list[str | RichText]] = [["Item", "Details"]]
    for index in range(4):
        rich = RichText().font_size(10).line_height(14)
        for part in range(8):
            rich.span(f"R{index + 1}P{part + 1} ", bold=True)
            rich.span(
                "Long rich cell content wraps across pages without losing its link. ",
                link=f"https://example.com/row/{index + 1}/part/{part + 1}",
            )
        rows.append([f"Row {index + 1}", rich])
    frame.add(
        Table(rows).column_widths([48, 212]).cell_padding(5)
        .header(background="#16324f", color="#ffffff", repeat=True)
        .row_style(2, background="#e0f2fe").zebra("#f1f5f9")
        .font_size(10).line_height(14).stroke("#cbd5e1", 0.5)
    )
    return doc
