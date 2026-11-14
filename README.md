# smart-report

Modern PDF creation library for Python with a custom 4-pass layout engine on top of ReportLab canvas.

smart-report is designed for report-style PDFs: flow content, tables, fixed regions, layered backgrounds, watermarks, and precise element positioning can all be composed through chainable Python builders.

## Documentation

- [Chinese API reference](./docs/zh/api.md)
- [Chinese documentation index](./docs/zh/README.md)
- [Changelog](./CHANGELOG.md)

## Goals

- Keep the reliability of PDF-native rendering.
- Reduce the gap between classic PDF APIs and modern HTML/CSS mental models.
- Support both flow layout and layered composition.
- Make text, images, shapes, tables, headers, footers, and watermarks compose predictably.

## Current Capabilities

- Flow containers via `Frame`.
- Layered containers via `Canvas`.
- Absolute positioning inside containers.
- Repeating page overlays via `header()`, `footer()`, and `watermark()`.
- Automatic pagination for flow content, nested frames, fixed-height blocks, and conservative rich table-cell cases.
- Practical `flex`, `grid`, and `columns` layout modes.
- Report-oriented `Table` with column widths, auto-fit columns, row/cell minimum heights, alignment, padding, spans, headers, footers, zebra rows, borders, rounded corners, table-level background images, and repeated headers/footers.
- `Text`, `RichText`, `Image`, text-capable `Rect` badges, `Line`, and `Spacer` elements.
- Fixed-box text alignment, vertical alignment, letter spacing, block-level text shadows, RichText span-level line height, overflow clipping, and multiline ellipsis.
- PDF URL links through `Text.link(url)` and inline `RichText.span(..., link=url)` annotations.
- PNG/JPEG/SVG rendering, image bytes/data URLs, `contain()`, `cover()`, background images, and per-corner radii.
- Public font registration helpers, fallback fonts, font families, and optional Arabic/bidi typography preprocessing.
- Paint ordering through stacking contexts and `z-index`.
- In-memory rendering through `save_to_bytes()`.

## Install

```bash
uv sync
```

or:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

## Quick Start

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

## Layout Diagnostics

Use `doc.save("debug.pdf", debug_layout=True)` or `doc.save_to_bytes(debug_layout=True)`
on a builder or built `Document`. The debug copy draws blue node bounds, green
content boxes (including the page's available body area), orange rectangular clip
regions, and node names with physical page numbers after normal painting. Add
`.name("summary-card")` to make labels and warnings useful. See
[`examples/layout_debug.py`](examples/layout_debug.py).

Debug rendering does not change layout or pagination. Nodes outside the physical
page emit `LayoutOverflowWarning` with their name, page and bounds; this checks
layout boxes, not visible glyph ink. Intentional absolute overflow can also warn.
Clip outlines show the layout engine's rectangular clip stack, not rounded masks
or per-cell geometry. Debug labels are diagnostic text and are included in PDF
text extraction; use the default output for delivery.

Page overlays use physical page coordinates: headers start at the top, footers at
the bottom, percentage overlay widths use the full page width, and page padding
reserves body space. Continuation pages deduct top and bottom page padding too.

## Development Checks

`tests/test_text_geometry.py` reads emitted text matrices, character spacing and
embedded font widths independently of the layout engine. It checks mixed Latin/CJK
alignment and indentation, font fallback, auto-shaped Arabic, and linked rich-text
continuations with mixed sizes and spacing. These checks compare PDF text advances
and annotation edges, not glyph ink bounds. They cover `plain` and `auto` typography;
OpenType ligature/kerning placement in `advanced` mode remains outside this suite.

To run just these samples and retain their PDFs for inspection:

```bash
SMART_REPORT_QA_DIR=/tmp/text-geometry uv run --no-sync python -m unittest discover -s tests -p test_text_geometry.py
```

`uv sync --locked` installs the development tools and PDF reader. For the complete
suite, including Gaussian shadows and raster regressions:

```bash
uv sync --locked --extra gaussian
uv run --no-sync python scripts/run_tests.py full
uv run --no-sync pyright
```

The full runner discovers all tests and fails on **any skipped test**. In a separate
environment without PDFium, run `uv sync --locked` followed by
`uv run --no-sync python scripts/run_tests.py base`; only the two raster-dependent
modules may be skipped. Use `uv sync --locked --no-dev` for runtime-only installation.

The locked SVG dependencies require system Cairo and pkg-config when building
Pycairo: `brew install cairo pkgconf` on macOS, or
`sudo apt-get install libcairo2-dev pkg-config` on Ubuntu. GitHub Actions checks
Python 3.10/3.14 on Linux and 3.14 on macOS, plus the base environment, builds both
distributions and imports the installed wheel outside the checkout.

Fixed Chinese, long rich-table and Yuanxi reports have reviewed page images under
`tests/fixtures/quality/{darwin,linux}/`. PDFium's unembedded base-14 font substitutes
differ by platform, so each has reviewed references. Full checks compare all pages at 72 dpi, tolerating at
most 0.1% of color channels changing by more than 24/255. Set
`SMART_REPORT_QA_DIR=/absolute/output/path` to retain PDFs and actual PNGs for review.
CI uploads them as artifacts. Baselines must be reviewed visually before replacement;
do not regenerate them just to make a failing check pass.

## Text Badges

`Rect` can render plain centered text directly, which is useful for labels, pills, and status badges without layering a separate `Canvas`, `Rect`, and `Text`.

```python
frame.add_rect("Paid") \
    .padding(vertical=3, horizontal=8) \
    .background("#dcfce7") \
    .color("#166534") \
    .font_size(9) \
    .radius(999)
```

## Tables and Rich Text

```python
from smart_report import Frame, Image, RichText, Table

rich = (
    RichText()
    .span("Revenue ")
    .span("+18%", font="Helvetica", font_size=14, color="#166534", bold=True, underline=True, link="https://example.com/growth", line_height=18)
    .br()
    .span("Enterprise renewals remained strong", font_size=10, color="#475569", italic=True)
    .width(180)
)

table = Table([["Metric", "Details"], ["Revenue", rich]]) \
    .row_height(0, 32) \
    .cell_height(1, 1, 48) \
    .header(background="#1d4ed8", color="#ffffff")
```

Table cell padding can be set globally with `.cell_padding(...)` and `.header_padding(...)`, or scoped through `.column_style(...)`, `.row_style(...)`, and `.cell_style(...)`. Scoped styles accept `padding=...` plus partial edges such as `padding_left`, `padding_vertical`, and `padding_horizontal`; partial values inherit unspecified edges with precedence `default/header -> column -> row -> cell`.

```python
table = Table(rows) \
    .cell_padding(vertical=6, horizontal=8) \
    .column_style(1, padding_left=14) \
    .row_style(3, padding_vertical=10) \
    .cell_style(3, 1, padding_right=18)
```

Padding is measured from each logical cell's own border. For merged cells, `.span(row, col, colspan=...)` uses the merged cell's outer border as the padding reference, not the border of a covered column. If a merged title row should align with text in column 1, add the covered column width to the anchor cell padding:

```python
Table(rows) \
    .column_widths([48, 246]) \
    .cell_padding(left=12, top=3, right=0, bottom=0) \
    .span(0, 0, colspan=2) \
    .cell_style(0, 0, padding_left=48 + 12)
```

Image cells are laid out as rich cell content. Table padding positions the image node's layout box inside the cell; `Image.contain()` then preserves the bitmap ratio and centers the bitmap inside that image box. For icon columns that should sit at the cell content's top-left corner, prefer a fixed-size image without `contain()` when the icon artwork already has the target ratio:

```python
icon = Image("ingredient.png").size(14, 14)

table = Table([[icon, "Ingredients: rice, ginger"]]) \
    .column_widths([48, 246]) \
    .cell_padding(left=12, top=3, right=0, bottom=0) \
    .valign("top")
```

If the cell needs to keep a wider content box but the icon itself must remain left/top anchored, wrap the image in a zero-padding `Frame`; the table stretches the wrapper, while the fixed-size child stays at the wrapper's flow origin:

```python
icon_cell = Frame().padding(0).add(
    Image("ingredient.png").size(14, 14)
)

Table([[icon_cell, "Ingredients: rice, ginger"]]) \
    .column_widths([48, 246]) \
    .cell_padding(left=12, top=3, right=0, bottom=0) \
    .valign("top")
```

Use `.contain()` when the image must stay fully visible inside a deliberately sized image box, and `.cover()` when it should fill that box and may crop. The unit for table sizes and padding is PDF points, not CSS pixels.

## Text Shadows

`Text.text_shadow(...)` and `RichText.text_shadow(...)` add block-level shadows without changing layout, wrapping or pagination. Positive `x` moves right; positive `y` moves down. Existing calls retain the `method="stroke"` vector-outline behavior.

For soft Gaussian shadows install the optional rasterizer:

```bash
pip install "smart-report[gaussian] @ https://github.com/yodew/smart-report/releases/download/v2.13.13/smart_report-2.13.13-py3-none-any.whl"
```

```python
frame.add_text("Soft title glow").font_size(28).color("#ffefcf").text_shadow(
    method="gaussian", sigma=3, dpi=300, color="#ff000080", knockout=True,
)

rich = RichText().span("Quarterly ", font_size=18).span("Highlights", font_size=24)
rich.text_shadow(method="gaussian", sigma=2, x=2, y=3, spread=1, color="#00000080")
```

`method="gaussian"` requires an explicit finite `sigma >= 0`, measured in PDF points, and `blur=0`. `sigma` is the Gaussian standard deviation, not a generic design-tool blur radius. `spread` expands the alpha mask before blurring, sampled to the nearest raster pixel. `dpi` must be finite and positive (default 300; 600 is supported). `knockout=True` uses a saturated glyph alpha mask and removes the original foreground glyph interior after blur, even when the shadow is offset, matching the hard-alpha/out filter pattern exported by Figma. It is only valid in Gaussian mode.

The renderer reuses already-laid-out PDF glyphs to generate a **local transparent shadow image**, then paints native vector text on top. Fonts, fallback glyphs, rich span sizes, letter spacing, alignment, first-line indent and line breaks share the foreground drawing path. Only the shadow is rasterized; text remains searchable/selectable. Glyph underlines and link annotations remain foreground decorations. Pillow's GaussianBlur is a fast numerical Gaussian approximation, not a native PDF filter or a claim of pixel-identical Figma rendering.

Missing Gaussian dependencies raise an actionable error; there is no silent downgrade to outlines. Local masks are limited to 16 million pixels before raster allocation; exceptionally large sigma/spread requests are rejected early. PDFium calls made by this renderer are serialized; applications calling PDFium independently must coordinate those calls too. Shadows respect existing clipping and do not enlarge layout boxes. Layer blur, background blur, inner shadows and per-span shadows are not supported.

The report example uses **actual Figma SVG filter exports**: source radii 6/8/12 px export `stdDeviation` 3/4/6 px; at 0.5 report scale these become `sigma=1.5/2/3` pt. This mapping is established for the bundled report samples, not assumed for every tool/effect.

Run `python examples/yuanxi_text_effects.py` after installing the optional extra. The four-page sample covers all 14 source nodes (including the overlapping score layer), compares no shadow / stroke / Gaussian knockout, and exercises mixed Chinese/Latin rich text, opacity, positive/negative offsets, spread and 300/600 dpi. Source text/effect records and SVG filters are in `examples/data/`; the bundled Yuanxi Demo Serif font is a renamed static instance of Source Han Serif and includes its original license and FONTLOG.

## First-line Text Indent

`Text.text_indent(...)` and `RichText.text_indent(...)` indent only the first rendered line. Use points such as `24`, or an `em` string such as `"2em"`; for Chinese paragraphs, `"2em"` is the recommended two-character first-line indent because it resolves against the element's effective font size.

Leading full-width spaces such as `"　　"` are not reliable for paragraph indentation with automatic wrapping: wrapping tokenizes whitespace and leading whitespace can be skipped or separated from the visible first line. `text_indent(...)` is layout geometry instead, so the first line gets an x offset and reduced available width while subsequent wrapped lines keep the normal width. Center/right alignment and PDF link annotations follow the visible indented line.

```python
frame.add_text("智能报告需要稳定的中文段落首行缩进……") \
    .font_size(12) \
    .line_height(20) \
    .text_indent("2em")

rich = RichText() \
    .font_size(12) \
    .line_height(20) \
    .text_indent("2em") \
    .span("富文本首行缩进", bold=True) \
    .span("同样支持自动换行和行内链接。", link="https://example.com")
```

See `examples/v2_13_text_indent.py` for a runnable Chinese Text/RichText example.

## Layered Reports

```python
from smart_report import Canvas, Frame, document

doc = document()
page = doc.page("A4")

background = Canvas().size(595, 842).absolute(0, 0).z(-20)
background.add_rect().absolute(0, 0).size(595, 842).background("#f4f7fb")
page.add(background)

summary = Frame().size(523, 120).absolute(36, 96).padding(16).background("#ffffff").z(10)
summary.add_text("Executive Summary").font_size(18)
page.add(summary)
```

See `examples/v2_11_layered_report.py` for a complete dashboard-style report.

## Background Images

`Frame`, `Canvas`, and `Table` support `.background_image(src, fit="cover", opacity=1.0)`. Sources match `Image`: local path strings, `pathlib.Path`, raw bytes, or `data:image/...;base64,...` strings. `fit` accepts `"stretch"`, `"contain"`, or `"cover"`; the image paints above the color background and below text, table cells, and borders.

```python
card = Frame().background("#ffffff").background_image("photo.png", fit="cover", opacity=0.12).radius(16)
table = Table(rows).background_image("watermark.png", fit="contain", opacity=0.08)
```

## Practical Image/Text Composition

Use existing primitives for common report cards instead of introducing custom components. A `Canvas` is best when image and text regions need exact locked positions, a `Frame` is best when a top image should flow into a bottom copy block, and `.background_image(...)` is best for title cards or report blocks where text/table content should remain above a subtle image layer.

```python
card = Canvas().size(520, 150).background("#ffffff").radius(18).overflow("hidden")
card.add_image("photo.jpg").absolute(0, 0).size(205, 150).cover()
card.add_text("Narrative card").absolute(230, 28).width(240).font_size(18)

table = Table(rows).background_image("texture.png", fit="cover", opacity=0.08)
```

See `examples/v2_12_image_text_composition.py` for a runnable A4 page combining side-by-side cards, stacked cards, image-backed title cards, and a table-over-background report block.

## Report Pattern Recipes

Business reports can be assembled as reusable section/card recipes without adding a new DSL. Use a background-image `Canvas` for the title/hero block, compact fixed `Canvas` or `Frame` cards for KPIs, an image/text `Canvas` for the executive summary, and a styled `Table` beside explanatory copy for data sections. Keep these recipes local to the report or example so the public API remains the existing primitives.

```python
hero = Canvas().height(144).background("#10243f").background_image("cover.jpg", fit="cover", opacity=0.48)
hero.add_text("Operating Review").absolute(24, 52).font_size(27).color("#ffffff")

kpi = Frame().width(162).padding(vertical=12, horizontal=16).background("#ffffff").radius(16)
kpi.add_text("Net revenue").font_size(9).color("#64748b")
kpi.add_text("$4.82M").font_size(22).color("#0f172a")
```

See `examples/v2_13_report_patterns.py` for a polished runnable A4 page demonstrating a background-image hero, KPI metric cards, an image/text executive summary, an annotated data table, and a multi-card dashboard/report section layout.

### Helper API Guidance

The current recipes intentionally keep helper functions local to examples or application code. Patterns like `kpi_card(...)`, `insight_card(...)`, or `add_summary_card(...)` tend to encode business copy, spacing, and visual hierarchy, so they are better maintained close to the report that owns them. Promote a helper into your own project only after two or three reports share the same structure; keep the helper returning ordinary `Canvas`, `Frame`, `Table`, or element builders so the underlying layout remains explicit.

smart-report does not add a built-in card/section DSL; the stable public API remains the existing primitives plus recipes that show how to combine them. For mixed inline typography, `RichText.span(..., line_height=...)` can raise an individual rich-text line box without changing plain `Text` behavior.

## Architecture

smart-report uses four explicit passes:

1. **Build**: chainable builders produce a `LayoutNode` tree.
2. **Pass 2 / Widths**: top-down width resolution.
3. **Pass 3 / Heights**: bottom-up height measurement and local positioning.
4. **Pass 4 / Render**: flatten to render items, sort by stacking context and `z-index`, then paint through ReportLab.

## Example Scripts

Run an example with:

```bash
.venv/bin/python examples/report_demo.py
```

Useful examples include:

- `examples/report_demo.py`
- `examples/paginated_report.py`
- `examples/layout_primitives.py`
- `examples/v2_6_table_auto_fit.py`
- `examples/v2_7_rich_text_links.py`
- `examples/v2_8_flex_wrap.py`
- `examples/v2_9_flex_refinements.py`
- `examples/v2_11_layered_report.py`
- `examples/v2_11_layered_table_region.py`
- `examples/v2_12_background_images.py`
- `examples/v2_12_image_text_composition.py`
- `examples/v2_13_report_patterns.py`
- `examples/v2_13_text_indent.py`
- `examples/v2_13_text_shadow.py`
- `examples/yuanxi_text_effects.py`
- `examples/zh_table_demo.py`

Optional PDF-regression assertions in `tests/test_table_v2.py` use `pypdf` when it is installed; without it, those PDF-only checks are skipped.


## Release Engineering

Use this checklist before publishing a package release or tagging a documentation/process release:

1. Confirm the worktree scope with `GIT_MASTER=1 git status --short` and `GIT_MASTER=1 git diff --stat`. Do not stage unrelated files.
2. Run validation:

```bash
uv sync --locked --extra gaussian
uv run --no-sync python scripts/run_tests.py full
uv run --no-sync pyright
```

3. Build the wheel and sdist using the declared development environment:

```bash
uv run --no-sync python -m build
```

4. Smoke-test the wheel, then import from outside the checkout:

```bash
uv pip install --reinstall --no-deps dist/smart_report-<version>-py3-none-any.whl
```

Then import from outside the repository root to confirm the installed wheel is used, not local source:

```bash
/absolute/path/to/smart-report/.venv/bin/python -c "import smart_report; print(smart_report.__version__, smart_report.__file__)"
```

6. Inspect the sdist when README links to documentation or examples. The sdist should include `CHANGELOG.md`, `docs/`, and the example scripts/resources declared in `MANIFEST.in`.
7. After validation and review pass, commit only the intended source/documentation/packaging metadata changes. Do not commit generated `dist/` or `build/` artifacts.
8. Create a new tag for that validated commit. Never move an existing release tag unless explicitly coordinating a release-history correction.
9. Push the branch and the new tag, then create a GitHub Release. In this project, commit, tag, push, and GitHub Release creation are the fixed final steps after validation and review pass:

```bash
GIT_MASTER=1 git push
GIT_MASTER=1 git push origin <tag>
gh release create <tag> dist/smart_report-<version>-py3-none-any.whl dist/smart_report-<version>.tar.gz --title <tag> --notes-file <notes-file>
```

PyPI publishing is separate and should only be performed when explicitly requested.

## Current Limitations

- `rowspan` content is kept together during pagination rather than split across pages.
- Images and SVG content paginate atomically; oversized images are not sliced.
- Rich table-cell pagination is conservative. Simple unspanned `Text`, `RichText`, and flow `Frame` cells can split, including rows with multiple simple frame cells; spanned rows, rich images, and complex frames remain atomic.
- `flex`, `grid`, and `columns` are practical layout primitives, not a complete CSS constraint solver.
- Flex row wrap is row-only; pagination keeps wrapped rows together where practical, but column wrap is not implemented.
- Advanced typography uses HarfBuzz for measurement when available, but rendering still uses ReportLab text APIs.
- Table auto-fit measures plain cells plus supported `Text`, `RichText`, and simple flow `Frame` cells; unsupported rich cells remain conservative.
- `Text.link(url)` is whole-text; use `RichText.span(..., link=url)` for inline rich-text links.

## License

MIT. See [LICENSE](./LICENSE).
