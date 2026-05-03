# AGENTS.md — layout/

## Overview

The 4-pass layout engine. Turns a raw `LayoutNode` tree into measured, positioned, and paginated pages ready for rendering.

---

## Pass Ordering

| Pass | File | Direction | What It Does |
|------|------|-----------|-------------|
| 2 | `pass2_widths.py` | Top-down | Resolves `resolved_width` for every node. Percentages use parent content box (width − padding.horizontal). Flow nodes subtract margin from available width. |
| 3 | `pass3_heights.py` | Bottom-up | Resolves `resolved_height` and `local_x`/`local_y`. Leaf nodes measure text using resolved width. Containers sum children. |
| Paginate | `paginate.py` | — | Splits overflowing frames and tables across pages. Clones nodes; preserves `source_row_index`. |
| 4 | `pass4_render.py` | Flatten | Walks tree to produce `RenderItem` list. Sorts by `(stacking_path, z_index, tree_order)`. |

**Call order in `Document.save()`**: pass2 → pass3 → paginate → pass2 again (overlays) → pass3 again → pass4.

---

## Key Data Structures

### `LayoutNode` (node.py)

- `resolved_width`, `resolved_height` — set by passes 2 and 3
- `local_x`, `local_y` — position within parent, set by pass 3
- `page_index`, `content["total_pages"]` — set before pass 4 for page number substitution
- `parent` — back-reference, excluded from `repr`
- `creates_stacking_context` — true for nodes with `z_index != 0` or `overflow == hidden`

### `RenderItem` (node.py)

- `absolute_bounds` — computed during pass 4 flattening
- `clip_rects` — stack of ancestor clip rectangles
- `sort_key` — tuple for stable paint ordering

---

## Where to Look

| Task | File | Notes |
|------|------|-------|
| Add a new node type | `node.py` + `pass2_widths.py` + `pass3_heights.py` + `pass4_render.py` | Must update all 4 passes plus `render/painters.py` |
| Fix width resolution bug | `pass2_widths.py` | Check `flow_width` vs `width_reference` logic for percentage handling |
| Fix height/position bug | `pass3_heights.py` | Leaf measurement uses `StringWidthFn` via `importlib`; container layout in `_layout_container()` |
| Fix table pagination | `paginate.py` + `table_model.py` | `_split_table_node` clones slices; `source_row_index` must survive |
| Fix render ordering | `pass4_render.py` | Check `stacking_path` and `tree_order_seed` |
| Add table feature | `table_model.py` + `containers/table.py` | Style precedence: cell → row → column → table |

---

## Layout Conventions

- **Points** are the base unit everywhere.
- **Flow layout**: children stack vertically. `local_y` accumulates previous child height + margin.
- **Absolute layout**: `local_x`/`local_y` come from `style.left`/`style.top`, unaffected by siblings.
- **Padding** reduces the content box available to children. **Margin** reduces the space the node itself occupies in flow layout.
- Pass 3 uses `importlib.import_module("smart_report.render.rl_adapter")` to get `StringWidthFn` for text measurement. This avoids a circular import.

---

## Anti-Patterns

- **Do not mutate `node.children` during pass 2 or 3.** Resolved values should not depend on child order changes mid-pass.
- **Never drop `source_row_index` when cloning table nodes.** Cell styles (`.cell_style()`, `.row_style()`) are looked up by `source_row_index`, not `row_index`. If pagination loses it, styles break across pages.
- **Do not assume `resolved_height` is available during pass 2.** Heights are computed bottom-up in pass 3.
- **Don't add a new `node_type` without adding its painter to `render/painters.py`.** Pass 4 skips unregistered types silently.

---

## Table Model Internals

`table_cell_boxes(node, x, y, width, height)` returns a list of `TableCellBox` dataclasses.

Style precedence (highest wins):
1. `cell_style(row, col)`
2. `row_style(row)`
3. `column_style(col)`
4. Table defaults (font, color, padding, etc.)
5. Header style (for header rows)

`table_height()` measures text per-cell using the resolved column widths and cell padding. It does not account for table borders.

`table_column_widths()` handles overflow by proportionally scaling down columns that exceed the available width.
