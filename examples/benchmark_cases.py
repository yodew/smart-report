"""Fixed deterministic workloads; performance is measured outside this module."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from typing_extensions import assert_never

from smart_report import DocumentBuilder, Frame, Table, document, register_font

BenchmarkCase = Literal["table", "chinese", "shadows"]


def build_case(case: BenchmarkCase, scale: int) -> DocumentBuilder:
    """Scale item counts, keeping geometry and content deterministic."""
    doc = document()
    match case:
        case "table":
            rows = [["ID", "Region", "Revenue", "Status"]]
            rows.extend([
                f"ROW-{index:05d}", f"Region {index % 12}", f"{index * 125:,}", "Confirmed",
            ] for index in range(600 * scale))
            frame = Frame()
            frame.add(Table(rows).column_widths([80, 120, 160, 160]).font_size(10)
                      .line_height(12).cell_padding(4).header(repeat=True))
            doc.page("A4").padding(36).add(frame)
        case "chinese":
            register_font("BenchmarkSans", Path(__file__).parent / "fonts/SourceHanSansSC-Normal.ttf")
            frame = Frame()
            doc.page("A4").padding(36).add(frame)
            for index in range(80 * scale):
                frame.add_text(
                    f"段落{index:04d}：" + "中文长报告应保持换行、缩进和跨页文字完整，测量结果用于发现性能变化。" * 5
                ).font("BenchmarkSans").font_size(12).line_height(18).text_indent("2em").margin(bottom=8)
        case "shadows":
            for start in range(0, 80 * scale, 10):
                page = doc.page("A4").padding(0)
                for row in range(10):
                    page.add_text(f"Shadow report {start + row:04d}") \
                        .absolute(36, 36 + row * 72).size(500, 36).font_size(20) \
                        .text_shadow(method="gaussian", sigma=2, dpi=300, x=2, y=2, color="#00000080")
        case unreachable:
            assert_never(unreachable)
    return doc
