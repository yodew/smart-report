# smart-report

Modern PDF creation library for Python with a custom 4-pass layout engine on top of ReportLab canvas.

中文文档：

- [中文 API 文档](./docs/zh/api.md)

## Goals

- Keep the reliability of PDF-native rendering
- Reduce the gap between classic PDF APIs and modern HTML/CSS mental models
- Support both flow layout and layered composition
- Make text, images, and shapes overlap through `z-index`

## Current capabilities

- Flow containers via `Frame`
- Layered containers via `Canvas`
- Absolute positioning inside `Canvas`
- Repeating page overlays via `header()`, `footer()`, and `watermark()`
- Basic automatic pagination for flow content
- Deeper pagination for nested frames and fixed-height blocks
- Practical `flex`, `grid`, and `columns` container layout modes
- Table column widths, alignment, cell padding, `rowspan` / `colspan`, header styling, zebra rows, rounded borders, and repeated headers on pagination
- Public font registration helpers and width-based CJK text wrapping
- PNG and SVG image rendering
- Top-down width resolution and bottom-up height measurement
- Paint ordering through `z-index`
- `Text`, `Rect`, `Line`, `Image`, `Spacer`, and report-oriented `Table`

## v1.3 status

- Chinese API documentation is available in `docs/zh/api.md`
- Table v2 supports column widths, alignment, padding, `rowspan`, `colspan`, header styling, zebra rows, rounded borders, repeated headers, and row/column/cell style overrides
- CJK text wraps by measured glyph width across text, table measurement, pagination, and rendering
- Fonts can be registered from the top-level API with `register_font(...)`, including fallback chains for mixed-language text
- Chinese runnable examples live in `examples/`, including `examples/zh_table_demo.py`
- Layout primitives are available through `.flex(...)`, `.grid(...)`, and `.columns(...)`
- Public API exports and validation behavior are stabilized for 1.0
- v1.1 adds rich table cells, pagination controls, table footers/subtotals, configurable borders, and image fit/bytes support
- v1.2 adds conservative rich table-cell pagination: a single unspanned `Frame` cell can split across table slices while repeated headers/footers and logical row styles are preserved
- v1.3 extends conservative rich table-cell pagination to single unspanned `Text` cells

## Table spans

```python
Table([
    ["Region", "Revenue", "Growth"],
    ["North", "$120K", "+8%"],
    ["", "$96K", "+5%"],
]).span(1, 0, rowspan=2)
```

## Layout primitives

```python
cards = Frame().grid(3, gap=10)
cards.add_text("Revenue").padding(10).background("#f8fafc")
cards.add_text("Growth").padding(10).background("#f8fafc")

summary = Frame().flex("row", gap=12)
summary.add_text("A")
summary.add_text("B")

notes = Frame().columns(2, gap=16)
notes.add_text("Long note one")
notes.add_text("Long note two")
```

## v1.1 report controls

```python
from smart_report import Frame, Image, Table

rich_cell = Frame().padding(4)
rich_cell.add_text("Nested content in a table cell")

table = (
    Table([["Metric", "Details"], ["Revenue", rich_cell]])
    .footer([["Total", "$216K"]], repeat=True, background="#e2e8f0")
    .borders("#94a3b8", width=0.5, inner_width=0.25, outer_width=1.5)
    .cell_border(1, 0, color="#2563eb", width=2)
)

Frame().add_text("Section title").keep_with_next()
Frame().page_break_before()
Image("chart.png").cover().radius(8)
```

## v1.3 rich-cell pagination

```python
details = Frame().padding(4).background("#f8fafc")
for index in range(20):
    details.add_text(f"Nested note {index + 1}").font_size(9).line_height(12)

table = (
    Table([["Metric", "Details"], ["Revenue", details]])
    .column_widths([90, "auto"])
    .header(background="#1d4ed8", color="#ffffff", repeat=True)
)
```

Single rich `Frame` or `Text` table cells with no `rowspan` / `colspan` can now split across pages. Spanned rows and rows with multiple rich cells are intentionally kept atomic so span boundaries remain valid.

## Font registration

```python
from smart_report import register_font

register_font("SourceHanSansSC-Normal", "examples/fonts/SourceHanSansSC-Normal.ttf", set_default=True, fallback=True)
```

## Install

```bash
uv sync
```

or

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

## Quick start

```python
from smart_report import Canvas, Frame, document

doc = document()
page = doc.page("A4")

hero = Canvas().height(160).background("#dbeafe")
hero.add_text("Hello smart-report").absolute(24, 24).font_size(24).color("#1e3a8a").z(2)
page.add(hero)

content = Frame().padding(24)
content.add_text("Flow content below the hero block.").font_size(12)
page.add(content)

doc.save("output.pdf")
```

## Repeating overlays and page numbers

```python
from smart_report import Frame, document

doc = document()

doc.header().height(40).add_text("Page {page_number} / {total_pages}").absolute("78%", 12)
doc.footer().height(28).add_text("Confidential").absolute(24, 8)
doc.watermark().height(200).opacity(0.08).add_text("DRAFT").absolute(170, 280)

page = doc.page("A4")
frame = Frame().padding(36)
for _ in range(30):
    frame.add_text("Long content that will flow onto later pages.")
page.add(frame)

doc.save("paginated.pdf")
```

## Margin and padding arguments

Prefer named arguments because the coordinate order is explicit:

```python
Canvas().margin(top=24, right=24, bottom=20, left=24)
Frame().padding(vertical=24, horizontal=32)
Text("Title").margin(bottom=16)
```

Tuple forms are still supported for compatibility:

```python
margin(24)                  # all sides
margin((24, 32))            # vertical, horizontal
margin((24, 24, 20, 24))    # top, right, bottom, left
```

## Architecture

`smart-report` uses four explicit passes:

1. **Build** – produce a `LayoutNode` tree
2. **Pass 2 / Widths** – resolve widths top-down
3. **Pass 3 / Heights** – measure content bottom-up and assign local positions
4. **Pass 4 / Render** – flatten to a render list, sort by stacking context + `z-index`, then paint

## Example scripts

- `examples/flow_layout.py`
- `examples/layered_canvas.py`
- `examples/report_demo.py`
- `examples/paginated_report.py`
- `examples/layout_primitives.py`
- `examples/v1_1_features.py`
- `examples/v1_2_features.py`
- `examples/v1_3_features.py`
- `examples/zh_table_demo.py`

Run one with:

```bash
.venv/bin/python examples/report_demo.py
```

## License

MIT. See [LICENSE](./LICENSE).

## Stability

The v1.3 release expands table pagination while preserving the v1.0 builder API. Future work should remain backward-compatible unless a major version bump is planned.

## Current limitations

- `rowspan` content is kept together during pagination rather than split across pages
- Pagination still keeps images atomic
- Rich table-cell pagination is conservative: only a single unspanned rich `Frame` or `Text` cell is split; spanned or multi-rich-cell rows remain atomic
- Flex/grid/columns are practical layout primitives, not a complete CSS constraint solver
- `height="auto"` with percentage-based absolute `top` values follows a simplified rule
