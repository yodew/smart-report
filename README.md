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
- Table column widths, alignment, cell padding, header styling, zebra rows, and repeated headers on pagination
- PNG and SVG image rendering
- Top-down width resolution and bottom-up height measurement
- Paint ordering through `z-index`
- `Text`, `Rect`, `Line`, `Image`, `Spacer`, and report-oriented `Table`

## v0.3 status

- Chinese API documentation is available in `docs/zh/api.md`
- Table v2 supports column widths, alignment, padding, header styling, zebra rows, repeated headers, and row/column/cell style overrides
- Chinese runnable examples live in `examples/`, including `examples/zh_table_demo.py`

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
- `examples/zh_table_demo.py`

Run one with:

```bash
.venv/bin/python examples/report_demo.py
```

## License

MIT. See [LICENSE](./LICENSE).

## Current limitations

- No `rowspan` / `colspan` yet
- Pagination is currently optimized for flow content inside `Frame`
- Very large single non-text, non-table blocks are moved rather than deeply split
- No flexbox/grid constraint solver yet
- `height="auto"` with percentage-based absolute `top` values follows a simplified rule
