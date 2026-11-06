"""Verify every shadowed report text node against its exported Figma SVG parameters.

Install: uv pip install -e '.[gaussian]'
Run: python examples/yuanxi_text_effects.py [output.pdf]
The first three pages preserve all 14 source nodes, including the overlapping score.
The fourth page exercises rich text, offsets, opacity, spread and raster resolution.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal, TypedDict

from smart_report import Canvas, RichText, document, register_font
from smart_report._builder_core import DocumentBuilder

ROOT = Path(__file__).resolve().parent
FONT = "YuanxiSerifBold"


class Color(TypedDict):
    r: float
    g: float
    b: float
    a: float


class Offset(TypedDict):
    x: float
    y: float


class Effect(TypedDict):
    radius: float
    spread: float
    color: Color
    offset: Offset


class Paint(TypedDict):
    color: Color
    opacity: float


class Case(TypedDict):
    id: str
    page: str
    characters: str
    reportCharacters: str
    fontSize: float
    fills: list[Paint]
    effects: list[Effect]


def _color(value: Color, opacity: float = 1) -> str:
    return f"rgba({round(value['r'] * 255)}, {round(value['g'] * 255)}, {round(value['b'] * 255)}, {value.get('a', 1) * opacity})"


def _page(doc: DocumentBuilder, title: str, number: int) -> Canvas:
    sheet = Canvas().size(595, 842).background("#100d0c").padding(0)
    doc.page((595, 842)).padding(0).add(sheet)
    sheet.add_text(title).absolute(28, 24).font(FONT).font_size(20).color("#fee7b8")
    sheet.add_text("元息健康报告 / Gaussian text-shadow verification").absolute(
        28, 60
    ).font(FONT).font_size(9).color("#bca06d")
    sheet.add_text(f"{number:02d} / 04").absolute(520, 810).font_size(9).color(
        "#bca06d"
    )
    return sheet


def main(output: Path) -> None:
    register_font(FONT, str(ROOT / "fonts/SourceHanSerifCN-Bold.ttf"))
    # Bundled, trusted Figma exports: preserve original fields verbatim for auditing.
    cases: list[Case] = json.loads((ROOT / "data/yuanxi-shadow-text.json").read_text())
    svg_specs = json.loads((ROOT / "data/yuanxi-shadow-svg.json").read_text())
    deviations = {v["id"]: v["stdDeviation"] for v in svg_specs}
    doc = document().metadata(title="元息健康报告 - 文字阴影验证")
    for page_index in range(3):
        sheet = _page(doc, "文字阴影 · 原稿节点逐项验证", page_index + 1)
        for x, label in (
            (28, "原始文字"),
            (210, "兼容描边模式"),
            (392, "高斯阴影 + knockout"),
        ):
            sheet.add_text(label).absolute(x, 100).font(FONT).font_size(10).color(
                "#bca06d"
            )
        for row, case in enumerate(cases[page_index * 5 : page_index * 5 + 5]):
            y = 128 + row * 132
            effect = case["effects"][0]
            sigma = deviations[case["id"]] * 0.5
            note = f"P{case['page']} · {case['id']}  |  radius {effect['radius']:g}px → σ {sigma:g}pt"
            sheet.add_text(note).absolute(28, y).font_size(8).color("#bca06d")
            methods: tuple[Literal["none", "stroke", "gaussian"], ...] = (
                "none",
                "stroke",
                "gaussian",
            )
            for column, method in enumerate(methods):
                x = 28 + column * 182
                sheet.add_rect().absolute(x, y + 20).size(170, 92).background(
                    "#211914"
                ).radius(6)
                fill = case["fills"][0]
                text = (
                    sheet.add_text(case["reportCharacters"])
                    .absolute(x + 10, y + 38)
                    .size(150, 64)
                    .font(FONT)
                )
                text.font_size(case["fontSize"] * 0.5).line_height(
                    case["fontSize"] * 0.72
                ).valign("middle")
                text.color(_color(fill["color"], fill["opacity"]))
                if method == "stroke":
                    text.text_shadow(
                        blur=effect["radius"] * 0.5,
                        spread=effect["spread"] * 0.5,
                        x=effect["offset"]["x"] * 0.5,
                        y=effect["offset"]["y"] * 0.5,
                        color=_color(effect["color"]),
                    )
                if method == "gaussian":
                    text.text_shadow(
                        method="gaussian",
                        sigma=sigma,
                        knockout=True,
                        dpi=300,
                        x=effect["offset"]["x"] * 0.5,
                        y=effect["offset"]["y"] * 0.5,
                        spread=effect["spread"] * 0.5,
                        color=_color(effect["color"]),
                    )
    sheet = _page(doc, "富文本与边界效果验证", 4)
    for i, (label, dpi, sigma, x, y, spread) in enumerate(
        (
            ("红色辉光 / 半透明 / 300dpi", 300, 3, 0, 0, 0),
            ("橙色阴影 / 向右下偏移", 300, 2, 5, 4, 0),
            ("绿色辉光 / spread 1pt / 600dpi", 600, 3, 0, 0, 1),
            ("负向偏移 / 600dpi", 600, 2, -4, -3, 0),
        )
    ):
        top = 125 + i * 155
        shade = ("#ff000080", "#ff8039", "#00755e", "#ffe6b2")[i]
        sheet.add_text(label).absolute(28, top).font(FONT).font_size(11).color(
            "#bca06d"
        )
        rich = (
            RichText()
            .font(FONT)
            .span("恢复能力 ", font_size=24, color="#ffefcf")
            .span("Recovery", font="Helvetica", font_size=18, color="#fee7b8")
            .br()
            .span("中文、mixed sizes、换行与原生文字", font_size=14, color="#ffefcf")
        )
        rich.absolute(38, top + 35).size(510, 90).line_height(34).letter_spacing(
            0.5
        ).align("center")
        rich.text_shadow(
            method="gaussian",
            sigma=sigma,
            dpi=dpi,
            x=x,
            y=y,
            spread=spread,
            color=shade,
            knockout=i in (1, 3),
        )
        sheet.add(rich)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    print(f"Wrote {output} (14 source nodes, 4 pages)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "yuanxi_text_effects.pdf")
