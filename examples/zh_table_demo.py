"""中文表格能力示例。"""

from pathlib import Path

from smart_report import Frame, Table, document, register_font

FONT_DIR = Path(__file__).with_name("fonts")
FONT_NORMAL = "SourceHanSansSC-Normal"
FONT_MEDIUM = "SourceHanSansSC-Medium"
FONT_BOLD = "SourceHanSansSC-Bold"


def register_demo_fonts() -> None:
    register_font(FONT_NORMAL, FONT_DIR / "SourceHanSansSC-Normal.ttf", set_default=True, fallback=True)
    register_font(FONT_MEDIUM, FONT_DIR / "SourceHanSansSC-Medium.ttf")
    register_font(FONT_BOLD, FONT_DIR / "SourceHanSansSC-Bold.ttf")


def main() -> None:
    register_demo_fonts()

    doc = document()
    page = doc.page("A4")

    frame = Frame().padding(32)
    frame.add_text("中文表格示例").font(FONT_BOLD).font_size(20).color("#0f172a").margin(bottom=16)
    frame.add_text(
        "这个示例展示列宽、对齐、单元格内边距、跨行单元格、表头样式、斑马纹、圆角边框以及跨页重复表头。"
    ).font(FONT_MEDIUM).font_size(12).color("#475569").margin(bottom=8)
    frame.add_text("标题使用 Bold，说明使用 Medium，表格内容使用 Normal。").font(FONT_NORMAL).font_size(10).color("#64748b").margin(bottom=20)

    rows = [["地区", "收入", "增长", "说明"]]
    for index in range(1, 24):
        rows.append([
            f"区域 {index}",
            f"¥{index * 120}K",
            f"+{(index % 8) + 3}%",
            "续约稳定企业客户增长明显用于测试中文连续文本换行。" if index % 2 == 0 else "新签项目增加渠道反馈积极无需空格也能换行。",
        ])

    frame.add(
        Table(rows)
        .column_widths([90, 80, 60, "auto"])
        .align(["left", "right", "right", "left"])
        .cell_padding(vertical=8, horizontal=10)
        .header_padding(vertical=10, horizontal=12)
        .header(background="#1d4ed8", color="#ffffff", repeat=True)
        .header_style(font=FONT_BOLD, font_size=11, line_height=14, align="center")
        .zebra("#f8fafc")
        .span(1, 0, rowspan=2)
        .span(5, 2, colspan=2)
        .row_style(3, background="#ecfeff")
        .column_style(2, color="#166534")
        .cell_style(6, 1, background="#dcfce7", color="#166534", align="right")
        .font(FONT_NORMAL)
        .font_size(10)
        .line_height(13)
        .color("#111827")
        .background("#ffffff")
        .stroke("#cbd5e1", 1)
        .radius(12)
    )

    page.add(frame)
    doc.save("examples/zh_table_demo.pdf")


if __name__ == "__main__":
    main()
