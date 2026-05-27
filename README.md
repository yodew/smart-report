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
- Public font registration helpers, width-based CJK text wrapping, and optional Arabic/bidi typography preprocessing
- PNG and SVG image rendering
- Top-down width resolution and bottom-up height measurement
- Paint ordering through `z-index`
- `Text`, `Rect`, `Line`, `Image`, `Spacer`, and report-oriented `Table`
- Table auto-fit columns: content-based sizing for plain-text cells with min/max constraints
- Whole-Text URL links via `Text.link(url)` for external PDF link annotations

## v2.4 status

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
- v1.5 extends conservative rich table-cell pagination to rows with multiple unspanned rich `Text` cells
- v2.0 resolves percentage absolute `top` inside auto-height containers and locks practical `flex`, `grid`, and `columns` semantics with regression coverage
- v2.1 supports mixed unspanned rich `Text` + `Frame` table rows, keeps rich `Image` cells atomic, and makes `flex("column", gap=...)` honor gaps
- v2.2 adds `typography("auto")`, `text_direction("rtl")`, and `shape_text(...)` for Arabic-script reshaping and bidi display ordering across text, tables, measurement, pagination, and rendering
- v2.2.1 updates the typography example to register and use bundled Noto Naskh Arabic fonts so Arabic output does not fall back to Helvetica
- v2.3 adds font-family registration, fallback-aware HarfBuzz-backed advanced width measurement, and mixed-script typography examples while keeping ReportLab canvas text rendering
- v2.4 adds named sections with scoped overlays, section page placeholders, PDF metadata, and automatic section outlines
- v2.6 adds `Table.auto_fit_columns()` for automatic column sizing based on plain-text natural widths, with Fit Then Clamp behavior and optional min/max constraints
- v2.7 adds `Text.link(url)` for whole-text PDF external URL link annotations, including linked rich `Text` table cells
- v2.8 adds row-only flex wrapping via `.flex("row", wrap=True)` with uniform gap on both axes
- v2.9 adds flex `justify`, `align`, `row_gap`, and `column_gap` for finer control over item placement

## v2.8 flex row wrap

```python
cards = Frame().flex("row", gap=10, wrap=True).width(480)
cards.add_text("Card 1").width(140).padding(10).background("#dbeafe")
cards.add_text("Card 2").width(140).padding(10).background("#dbeafe")
cards.add_text("Card 3").width(140).padding(10).background("#dbeafe")
cards.add_text("Card 4").width(140).padding(10).background("#dbeafe")
```

`flex("row", wrap=True)` lays out children left to right and wraps to the next row when the combined width (including gaps) exceeds the container width. The same `gap` value applies horizontally between items and vertically between wrapped rows. Children with explicit widths keep those widths; text children without widths measure to their natural text width. A single child wider than the container is placed alone on its row and may overflow.

**Limitations**: row-only wrapping; no column wrap. Not a full CSS flexbox implementation. No row-aware pagination guarantee across page breaks.

## v2.9 flex refinements

```python
row = Frame().flex("row", gap=8, justify="center", align="center").width(400)
row.add_text("A").width(80).padding(8).background("#dbeafe")
row.add_text("B").width(80).padding(8).background("#dbeafe")

wrapped = Frame().flex("row", gap=8, wrap=True, row_gap=20, column_gap=8).width(300)
wrapped.add_text("Item 1").width(80).padding(8).background("#fef3c7")
wrapped.add_text("Item 2").width(80).padding(8).background("#fef3c7")

col = Frame().flex("column", gap=8, justify="space-between", align="center").width(300).height(200)
col.add_text("Top").padding(8).background("#ede9fe")
col.add_text("Bottom").padding(8).background("#ede9fe")
```

`flex()` gains four new keyword arguments: `justify`, `align`, `row_gap`, and `column_gap`.

`justify` controls main-axis placement. Supported values: `start`, `center`, `end`, `space-between`. Works for both non-wrapped rows and wrapped rows (per-row). Column justify distributes vertical space only when the parent has an explicit content height; auto-height column justify is a no-op.

`align` controls cross-axis placement. Supported values: `start`, `center`, `end`. In row mode, this offsets items vertically within the tallest row height. In column mode, this offsets items horizontally against the content width.

`row_gap` and `column_gap` set axis-specific spacing. Row and wrapped-row horizontal spacing uses `column_gap` (falls back to `gap`). Wrapped-row vertical advancement and column stacking use `row_gap` (falls back to `gap`). Column stacking ignores `column_gap`.

**Limitations**: not full CSS flexbox. No `stretch`, `space-around`, or `space-evenly`. No flex grow/shrink/basis. No reverse directions. No column wrap. No row-aware pagination guarantee.

## v2.6 table auto-fit

```python
table = (
    Table([
        ["Region", "Revenue", "Growth"],
        ["APAC", "$1.20M", "+18%"],
        ["EMEA", "$0.98M", "+11%"],
        ["North America", "$1.60M", "+23%"],
    ])
    .auto_fit_columns()
    .cell_padding(vertical=7, horizontal=10)
    .header(background="#1d4ed8", color="#ffffff")
    .zebra("#f8fafc")
)
```

`auto_fit_columns()` sizes each column to its natural plain-text width plus cell padding. Pass a list of column indexes to fit only those columns; the rest keep their explicit widths. Legacy `column_widths(["auto"])` without `.auto_fit_columns()` still uses equal-share distribution.

Natural widths follow Fit Then Clamp behavior: text width is measured first, then `column_min_widths` and `column_max_widths` constraints are applied. Narrow fitted tables are not stretched to fill the available width. Only plain-string cells contribute natural widths; rich `Frame`/`Text`/`Image` cells are excluded.

## v2.7 rich text links

```python
from smart_report import Text

linked = Text("Visit docs").link("https://example.com/docs").color("#2563eb")
```

`Text.link(url)` attaches a PDF external URL annotation to the whole text node. Clicking anywhere on the text opens the linked URL in a browser. Links work in both standalone `Text` nodes inside a `Frame` and as rich `Text` table cells.

No automatic link styling is applied. Users can opt into color or other visual cues using the existing Text style APIs. Whole-text links only; there are no inline substring links, no markdown/HTML parsing, and no arbitrary annotation API.

```python
from smart_report import Table, Text

link_cell = Text("Documentation").link("https://example.com/docs")
table = Table([["Section", "Link"], [link_cell, "Official docs"]])
```

Rich `Text` table cells support links through the same `Text.link(url)` API. The entire cell text becomes the clickable area. Plain string table cells do not support links.

## v2.3 advanced typography

```python
from smart_report import register_font_family

register_font_family(
    "NotoNaskhArabic",
    regular="examples/fonts/NotoNaskhArabic-Medium.ttf",
    bold="examples/fonts/NotoNaskhArabic-Bold.ttf",
    fallback=True,
)

frame.add_text("مرحبا smart-report") \
    .font_family("NotoNaskhArabic") \
    .typography("advanced") \
    .text_direction("rtl")
```

`typography("advanced")` uses HarfBuzz metrics for fallback-aware, shaping-aware width measurement and line wrapping when registered TTF fonts are available. Rendering remains on ReportLab canvas text APIs, so exact glyph positioning, arbitrary glyph-ID rendering, vertical writing, color fonts, and full text-engine behavior remain out of scope.

## v2.4 section templates and document structure

```python
from smart_report import document

doc = document()
doc.metadata(title="Report", author="team", subject="Q4 summary")

intro = doc.section("Introduction", page_numbering="restart")
intro.header().height(28).add_text(
    "Introduction  {section_page_number}/{section_total_pages}"
).absolute(36, 8)
intro.footer().height(24).add_text(
    "Intro footer  {section_name} {section_page_number}/{section_total_pages}"
).absolute(36, 6)

page = intro.page("A4")
frame = page.add_frame().padding(36)
frame.add_text("Introduction").font_size(18)

body = doc.section("Body", page_numbering="restart")
body.suppress_watermark()
body_page = body.page("A4")

doc.save("report.pdf")
```

Sections control scoped overlays: a section's `header()` / `footer()` / `watermark()` override the corresponding global kind on that section's pages. `suppress_header()`, `suppress_footer()`, and `suppress_watermark()` remove inherited global overlays entirely. `{section_name}`, `{section_page_number}`, and `{section_total_pages}` are section-scoped placeholders, while `{page_number}` and `{total_pages}` remain absolute document-level values. Empty named sections produce no pages and no outline entries. Set `outline=False` to hide a section from the PDF outline.

## v2.2 typography

```python
from smart_report import Frame, shape_text

text = "مرحبا smart-report"

Frame().add_text(text).typography("auto").text_direction("rtl")
shape_text(text, "auto", "rtl")
```

`typography("auto")` applies Arabic-script reshaping and bidi display ordering before width measurement, wrapping, pagination, and final painting. Register an Arabic/Hebrew-capable TTF for production output; the default `Helvetica` font is not suitable for these scripts. The v2.2 typography example registers bundled Noto Naskh Arabic fonts before rendering Arabic text.

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

stack = Frame().flex("column", gap=8)
stack.add_text("First")
stack.add_text("Second")

notes = Frame().columns(2, gap=16)
notes.add_text("Long note one")
notes.add_text("Long note two")
```

## v2.0 absolute positioning in auto-height containers

```python
panel = Frame().padding(12).width(240)
panel.add_text("Flow content determines the auto height.")
panel.add_text("Badge").absolute(0, "50%").background("#dbeafe")
```

Percentage absolute `top` values now resolve against the final auto content height. Values at or above `100%` are rejected for auto-height parents because they cannot produce a finite containing height.

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

## v1.5 rich-cell pagination

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

Single rich `Frame` or `Text` table cells with no `rowspan` / `colspan` can split across pages. Rows with multiple rich `Text` cells can also split when every rich cell in that row is `Text`. v2.1 also supports mixed unspanned rich `Text` + `Frame` rows. Spanned rows and rows containing rich `Image` cells are intentionally kept atomic so span boundaries remain valid.

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
- `examples/v1_5_features.py`
- `examples/v2_0_features.py`
- `examples/v2_1_features.py`
- `examples/v2_2_typography.py`
- `examples/v2_3_advanced_typography.py`
- `examples/v2_4_document_structure.py`
- `examples/v2_6_table_auto_fit.py`
- `examples/v2_7_rich_text_links.py`
- `examples/v2_8_flex_wrap.py`
- `examples/v2_9_flex_refinements.py`
- `examples/zh_table_demo.py`

Run one with:

```bash
.venv/bin/python examples/report_demo.py
```

## License

MIT. See [LICENSE](./LICENSE).

## Stability

The v2.9 release adds flex `justify`, `align`, `row_gap`, and `column_gap` for finer control over item placement, while preserving backward compatibility with the v2.8, v2.4, v2.6, and v2.7 builder API.

## Current limitations

- `rowspan` content is kept together during pagination rather than split across pages
- Pagination keeps images and SVG content atomic: if the current page lacks space, the whole image moves to the next page; oversized images are not sliced
- Rich table-cell pagination is conservative: single unspanned rich `Frame`/`Text` cells, rows whose rich cells are all unspanned `Text` cells, and mixed unspanned `Text` + `Frame` rows can split; spanned rows, rich images, and multi-Frame rows remain atomic
- Flex/grid/columns are practical layout primitives, not a complete CSS constraint solver
- Flex row wrap is row-only; no column wrap, no row-aware pagination guarantee
- v2.3 uses HarfBuzz for advanced measurement, but rendering still uses ReportLab text APIs; exact glyph positioning, arbitrary glyph-ID drawing, vertical writing, and color-font support are not guaranteed
- Table auto-fit (`auto_fit_columns`) works on plain-string cells only; rich `Frame`/`Text`/`Image` cells do not contribute natural widths in v2.6
- `Text.link(url)` is whole-text only; no inline substring links, no markdown/HTML parsing, no automatic link styling, no plain string table cell link API, and no arbitrary annotation API
