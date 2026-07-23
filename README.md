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
- Fixed-box text alignment, vertical alignment, letter spacing, overflow clipping, and multiline ellipsis.
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
from smart_report import RichText, Table

rich = (
    RichText()
    .span("Revenue ")
    .span("+18%", font="Helvetica", font_size=14, color="#166534", bold=True, underline=True, link="https://example.com/growth")
    .br()
    .span("Enterprise renewals remained strong", font_size=10, color="#475569", italic=True)
    .width(180)
)

table = Table([["Metric", "Details"], ["Revenue", rich]]) \
    .row_height(0, 32) \
    .cell_height(1, 1, 48) \
    .header(background="#1d4ed8", color="#ffffff")
```

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
- `examples/zh_table_demo.py`

Optional PDF-regression assertions in `tests/test_table_v2.py` use `pypdf` when it is installed; without it, those PDF-only checks are skipped.


## Release Engineering

Use this checklist before publishing a package release or tagging a documentation/process release:

1. Confirm the worktree scope with `GIT_MASTER=1 git status --short` and `GIT_MASTER=1 git diff --stat`. Do not stage unrelated files.
2. Run validation:

```bash
.venv/bin/python -m unittest tests.test_table_v2
.venv/bin/python -m unittest tests.test_document_structure
npx --yes pyright
```

3. Ensure local build tooling is available in the project virtual environment:

```bash
.venv/bin/python -m build --version
.venv/bin/python -m pip show build wheel setuptools
```

If tooling is missing, install it into `.venv` only:

```bash
.venv/bin/python -m pip install build wheel setuptools
```

4. Build wheel and sdist locally:

```bash
.venv/bin/python -m build
```

5. Smoke-test the artifacts:

```bash
.venv/bin/python -m pip install --force-reinstall --no-deps dist/smart_report-<version>-py3-none-any.whl
```

Then import from outside the repository root to confirm the installed wheel is used, not local source:

```bash
/home/yodew/projects/smart-report/.venv/bin/python -c "import smart_report; print(smart_report.__version__, smart_report.__file__)"
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
