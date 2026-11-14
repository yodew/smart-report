"""Fixed atomic-content cases for pagination checks and manual inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from typing_extensions import assert_never

from smart_report import DocumentBuilder, Frame, Image, Table, document

BoundaryCase = Literal["image", "rowspan", "complex"]


def boundary_report(case: BoundaryCase, height: float, *, intro: bool = False) -> DocumentBuilder:
    """Use a 120-point body on a 240x180 page; preserve atomic content size."""
    doc = document()
    body = Frame().padding(0)
    doc.page((240, 180)).padding(30).add(body)
    if intro:
        body.add_text("INTRO").height(60)
    match case:
        case "image":
            node = Image(Path(__file__).parent / "box.png").size(80, height)
        case "rowspan":
            node = Table([["MERGED", "ROW-A"], ["", "ROW-B"]]).header(0) \
                .column_widths([80, 100]).cell_padding(0).font_size(9) \
                .span(0, 0, rowspan=2).row_height(0, height / 2).row_height(1, height / 2)
        case "complex":
            cell = Frame().grid(2).height(height).background("#dbeafe")
            cell.add_text("LEFT").font_size(9)
            cell.add_text("RIGHT").font_size(9)
            node = Table([["CELL", cell]]).header(0).column_widths([40, 140]).cell_padding(0)
        case unreachable:
            assert_never(unreachable)
    body.add(node.name(f"atomic-{case}"))
    return doc
