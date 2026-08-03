"""Demonstrate first-line Text and RichText indentation for Chinese paragraphs."""

from __future__ import annotations

from pathlib import Path

from smart_report import Frame, RichText, document, register_font, set_default_font


OUTPUT = Path(__file__).with_name("v2_13_text_indent.pdf")
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def main() -> None:
    register_font("SourceHanSansSC-Normal", FONT_DIR / "SourceHanSansSC-Normal.ttf", fallback=True)
    set_default_font("SourceHanSansSC-Normal")

    paragraph = (
        "智能报告需要在自动换行后保持段落版式稳定。"
        "首行缩进应当作为布局几何处理，而不是在字符串前拼接全角空格。"
        "这样链接、对齐和分页都能跟随实际可见的第一行。"
    )

    doc = document()
    page = doc.page("A4")
    frame = Frame().padding(vertical=36, horizontal=42).background("#f8fafc")

    frame.add_text("Text.text_indent(\"2em\")") \
        .font_size(18) \
        .line_height(24) \
        .color("#0f172a") \
        .margin(bottom=14)
    text = frame.add_text(paragraph) \
        .width("100%") \
        .font_size(12) \
        .line_height(20)
    text.text_indent("2em").margin(bottom=28)

    frame.add_text("RichText.text_indent(\"2em\")") \
        .font_size(18) \
        .line_height(24) \
        .color("#0f172a") \
        .margin(bottom=14)
    rich = (
        RichText()
        .font_size(12)
        .line_height(20)
        .span("富文本也支持同样的首行缩进。", color="#1d4ed8", bold=True)
        .span("可以继续混合颜色、加粗和链接；缩进只影响第一条可见行，后续换行使用完整宽度。", color="#334155", link="https://example.com/text-indent")
        .width("100%")
    )
    rich.text_indent("2em")
    frame.add(rich)

    page.add(frame)
    doc.save(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
