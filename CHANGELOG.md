# Changelog

All notable changes to smart-report are summarized here. The latest released package version is `2.13.13`.

## 2.13.13

- Added PDF-level text geometry regressions comparing embedded font advances and text matrices against alignment, indentation and link annotation bounds, without new raster baselines.
- Covered Latin/CJK text with positive/negative spacing, fallback font switches, auto-shaped Arabic, and paginated rich spans with mixed sizes and spacing. `advanced` OpenType glyph placement remains outside this suite.
- Reused `SMART_REPORT_QA_DIR` and existing CI artifact uploads to retain sample PDFs; documented the focused check in English and Chinese. Runtime rendering behavior is unchanged.

## 2.13.12

- Added base/full development environments and GitHub Actions checks on Python 3.10/3.14 (Linux) and 3.14 (macOS), including all discovered tests, skip auditing, type checks, builds and an installed-wheel smoke test.
- Added reviewed raster and content regressions for Chinese reports, long linked rich-table cells and all four Yuanxi shadow pages; CI retains actual PDFs and page images; reviewed Linux/macOS references account for PDFium base-14 font substitution without loosening image thresholds.
- Added opt-in `save(..., debug_layout=True)` and `save_to_bytes(debug_layout=True)` overlays for node/content bounds, rectangular clip regions, names and page numbers, plus named `LayoutOverflowWarning` diagnostics for off-page layout boxes.
- Fixed page-padding offsets pushing headers/footers outside their physical anchors, and fixed continuation frames using physical page height instead of available body height.
- Extracted document builders, sections, rendering orchestration and page-level pagination while preserving existing public imports and runtime painter replacement.
- Updated English/Chinese development and API documentation, and included regression resources/check scripts in source distributions.

## 2.13.11

- Ships opt-in Gaussian Text/RichText shadows and the four-page Yuanxi verification example introduced in 2.13.10; existing stroke calls remain compatible.
- Renamed the bundled derived static font to Yuanxi Demo Serif to respect the upstream Reserved Font Name; retained Adobe copyright/OFL notices and added a FONTLOG. Glyph outlines, metrics, character maps and shaping tables are unchanged.
- Updated release-wheel installation URLs and example font registration for this packaged release.

## 2.13.10

- Added opt-in Gaussian `Text.text_shadow(...)` and `RichText.text_shadow(...)` rendering with explicit `sigma`, `dpi`, and Figma-style `knockout`; existing `blur` calls retain stroke behavior.
- Reused laid-out PDF glyphs for local alpha masks, preserving native selectable foreground text, alignment, fallback fonts and rich span geometry; added the optional `smart-report[gaussian]` PDFium dependency and bounded raster allocation.
- Fixed legacy shadow graphics-state leakage so outlined shadows no longer stroke foreground text.
- Added a four-page Yuanxi report example covering all 14 original shadow nodes, exported Figma SVG filter parameters, the licensed source font, and rich text/opacity/offset/spread/300-600 dpi checks.
- Expanded English and Chinese API documentation, including unit semantics, optional installation, clipping, threading and unsupported effects.
- Added PDF-level regression tests for soft alpha, text extraction, knockout, offsets, validation, missing optional dependencies and legacy foreground isolation.

## 2.13.9

- Fixed `RichText` letter-spacing measurement across adjacent spans so wrapping, centered alignment, underline widths, and link annotation rectangles match the rendered text advance.
- Added regression coverage showing plain `Text` letter spacing already participates in wrapping and centered drawing.

## 2.13.8

- Expanded Table documentation with scoped padding examples for merged cells, icon/text columns, and image cells.
- Clarified that `Image.contain()` centers the bitmap inside the image node's own box, while table padding positions that node inside the cell content box.

## 2.13.7

- Added scoped table cell padding controls to `Table.column_style(...)`, `Table.row_style(...)`, and `Table.cell_style(...)` using `padding`, per-edge, vertical, and horizontal keyword arguments.
- Resolved table padding during row-height measurement and cell box creation with inheritance precedence `default/header -> column -> row -> cell`, preserving unspecified edges for partial overrides.

## 2.13.6

- Added `Text.text_indent(...)` and `RichText.text_indent(...)` for first-line indentation using points or `em` units resolved against the effective node font size.
- Treated first-line indent as layout geometry for wrapping, alignment, link annotations, and RichText pagination continuations instead of relying on leading whitespace.
- Added Chinese paragraph documentation and a runnable `examples/v2_13_text_indent.py` demo recommending `text_indent("2em")`.

## 2.13.5

- Fixed `Text.text_shadow(...)` and `RichText.text_shadow(...)` blur/spread rendering so glow-style shadows use a single stroked text outline instead of multiple visible repeated text copies.

## 2.13.4

- Added block-level `Text.text_shadow(...)` and `RichText.text_shadow(...)` APIs with normalized typed shadow settings.
- Painted text shadows before main text using a bounded vector approximation for blur/spread; no native PDF blur filters, raster blur, span-level rich-text shadows, or layout behavior changes were added.

## 2.13.3

- Added `RichText.span(..., line_height=...)` for span-level line height control in mixed rich-text lines.
- Preserved explicit RichText span line heights through wrapping, serialization, pagination splits, and inline link annotation rectangles.

## 2.13.2

- Documented the section/card helper assessment from the `2.12.3` and `2.13.0` recipes.
- Kept helper functions as local recipe/application patterns instead of adding a built-in card or section DSL.

## 2.13.1

- Hardened background-image regression coverage for JPEG/SVG/data URL source rendering and paginated table slices.
- Added focused checks that table background-image settings survive pagination and still paint on each slice.

## 2.13.0

- Added a polished report section/card pattern recipe example showing a background-image hero, KPI cards, an image/text executive summary, an annotated data table, and a multi-card report section layout using existing primitives only.
- Documented report pattern recipes in the README and Chinese API reference without adding runtime helper API.

## 2.12.3

- Added a practical image/text composition example showing side-by-side cards, stacked cards, background-image title cards, and table-over-background report blocks using existing primitives.
- Documented image/text composition patterns in the README and Chinese API reference without adding new runtime API.

## 2.12.2

- Added `.background_image(src, fit="cover", opacity=1.0)` for `Frame`, `Canvas`, and table-level backgrounds using the same practical source shapes as `Image`.
- Painted container and table background images below content and borders, with rounded clipping where applicable.

## 2.12.1

- Hardened inline RichText link regression coverage for aligned annotation rectangles and query-string URL preservation.

## 2.12.0

- Added `RichText.span(..., link=url)` for inline PDF external URL annotations on rich-text spans.
- Preserved RichText span links through wrapping, pagination, and rich table-cell rendering.

## 2.11.17

- Added row-boundary pagination for `Frame().flex("row", wrap=True)` so wrapped visual rows stay together where practical.
- Updated flex wrap documentation and examples to describe the row-aware pagination behavior.

## 2.11.16

- Allowed unspanned table rows with multiple simple flow `Frame` rich cells to split across pagination slices.
- Kept spanned rows, rich images, and complex frame/table cells conservative and atomic during pagination.

## 2.11.15

- Expanded `Table.auto_fit_columns()` natural-width measurement to supported rich `Text`, `RichText`, and simple flow `Frame` cells.
- Kept unsupported rich table cells conservative while preserving auto-fit column widths through pagination slices.

## 2.11.14

- Surfaced recent RichText span styling, Rect text labels, and layered table-region examples in the main documentation and demo path.
- Added direct regression coverage for `Frame.add_rich_text(...)` and `RichText.clear()` builder behavior.

## 2.11.13

- Added `RichText.span(..., italic=True, underline=True)` for inline italic and underlined rich text fragments.
- Preserved RichText italic and underline styling through wrapping and pagination splits.

## 2.11.12

- Upgraded the fixed release workflow to require GitHub Release creation after tag push.

## 2.11.11

- Added text-capable `Rect` labels for badge/tag usage without manual Canvas layering.

## 2.11.10

- Added multiline `Text.text_overflow("ellipsis")` rendering for fixed-height text boxes while preserving table-cell ellipsis behavior.
- Fixed the project release workflow to require commit, tag, and push after validation and review pass.

## 2.11.9

- Moved release history into `CHANGELOG.md` and rewrote the README/API documentation as current-reference material.
- Added `MANIFEST.in` so source distributions include changelog, docs, example scripts, and example resources.
- Documented the release engineering checklist for validation, local artifact builds, sdist inspection, tagging, and pushing.

## 2.11.8

- Fixed image radius clipping for fitted images: `contain()` and `cover()` now apply corner radii after the image is scaled and positioned, so the visible fitted image area receives the expected rounded corners.

## 2.11.7

- Added per-corner `.radius(...)` values for images, rectangles, containers, and table outer borders.
- Supported `.radius(8)`, `.radius((top_left, top_right, bottom_right, bottom_left))`, and named corner arguments such as `.radius(top_left=10, bottom_right=10)`.

## 2.11.6

- Added `Text.text_overflow(...)` for fixed text boxes.
- Supported `"wrap"`, `"clip"`, and `"ellipsis"` overflow modes.
- Added RichText global and per-span letter spacing.

## 2.11.5

- Added table logical row and cell minimum heights.
- Added standalone `RichText` for styled inline spans without changing existing `Text` behavior.

## 2.11.3

- Added `Text.valign(...)` for vertical alignment inside fixed-height text boxes.
- Added `Text.letter_spacing(...)`.
- Made default line height follow `font_size * 1.2` unless explicitly overridden.

## 2.11.2

- Added `Text.align(...)` for left, center, and right alignment inside fixed-width text boxes.

## 2.11.1

- Accepted `pathlib.Path` image sources.
- Expanded API documentation for shapes, tables, colors, fonts, and shared chainable methods.

## 2.11

- Strengthened layered report rendering contracts.
- Added a fixed-region multi-layer report example with predictable background, content, watermark, header, and footer ordering.

## 2.10

- Added `save_to_bytes()` for in-memory PDF bytes.
- Documented async framework integration with `asyncio.to_thread` for avoiding event-loop blocking.

## 2.9

- Added flex `justify`, `align`, `row_gap`, and `column_gap` controls.

## 2.8

- Added row-only flex wrapping through `.flex("row", wrap=True)`.

## 2.7

- Added `Text.link(url)` for whole-text PDF external URL link annotations, including linked rich `Text` table cells.

## 2.6

- Added `Table.auto_fit_columns()` for plain-text natural-width column sizing.
- Added Fit Then Clamp behavior with optional column min/max width constraints.

## 2.4

- Added named sections with scoped header, footer, and watermark overlays.
- Added section page placeholders, PDF metadata, and automatic section outlines.
- Published Chinese API documentation.

## 2.3

- Added font-family registration.
- Added fallback-aware HarfBuzz-backed advanced width measurement and mixed-script typography examples while keeping ReportLab canvas text rendering.

## 2.2.1

- Updated typography examples to register bundled Noto Naskh Arabic fonts, avoiding Helvetica fallback for Arabic output.

## 2.2

- Added `typography("auto")`, `text_direction("rtl")`, and `shape_text(...)` for Arabic-script reshaping and bidi display ordering across measurement, wrapping, pagination, tables, and rendering.

## 2.1

- Supported pagination for unspanned mixed rich `Text` + `Frame` table rows.
- Kept rich `Image` table cells atomic.
- Made `flex("column", gap=...)` honor gaps.

## 2.0

- Resolved percentage absolute `top` inside auto-height containers against final content height.
- Locked practical `flex`, `grid`, and `columns` semantics with regression coverage.

## 1.5

- Extended conservative rich table-cell pagination to rows with multiple unspanned rich `Text` cells.

## 1.3

- Extended conservative rich table-cell pagination to a single unspanned `Text` cell.

## 1.2

- Added conservative rich table-cell pagination for a single unspanned `Frame` cell while preserving repeated headers/footers and logical row styles.

## 1.1

- Added rich table cells, pagination controls, table footers/subtotals, configurable borders, and image fit/bytes support.
