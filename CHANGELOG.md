# Changelog

All notable changes to smart-report are summarized here. The latest released package version is `2.11.8`.

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
