# AGENTS.md — smart-report

## Quick Start

Install dependencies (Python >= 3.10 required):

```bash
uv sync
```

Or with plain pip:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Run an example:

```bash
.venv/bin/python examples/report_demo.py
```

Run tests:

```bash
.venv/bin/python -m unittest tests.test_table_v2
```

Type-check (Pyright):

```bash
pyright
```

> There is no pytest, ruff, mypy, pre-commit, or CI config. Tests use `unittest`. Type checking uses `pyright` via `pyrightconfig.json`.

---

## Architecture

smart-report is a PDF generation library built on top of ReportLab. It uses a **4-pass layout engine**:

1. **Build** — chainable builders produce a `LayoutNode` tree (`_builder_core.py`)
2. **Pass 2 / Widths** — top-down width resolution (`layout/pass2_widths.py`)
3. **Pass 3 / Heights** — bottom-up height measurement and local positioning (`layout/pass3_heights.py`)
4. **Pass 4 / Render** — flatten to a render list, sort by stacking context + `z-index`, then paint (`layout/pass4_render.py`)

Pagination (`layout/paginate.py`) splits overflowing content across pages. The final paint layer delegates to ReportLab via `render/rl_adapter.py`.

---

## Key Files and Boundaries

| Path | Purpose |
|------|---------|
| `src/smart_report/__init__.py` | Public API: `document()`, `Canvas`, `Frame`, `Table`, `Text`, `Image`, `Rect`, `Line`, `Spacer` |
| `src/smart_report/_builder_core.py` | Core builder classes (`NodeBuilder`, `ContainerBuilder`, `DocumentBuilder`, `Document`). Also the `save()` orchestrator that wires all 4 passes together. |
| `src/smart_report/layout/node.py` | Core data structures: `LayoutNode`, `Style`, `Edges`, `RenderItem` |
| `src/smart_report/layout/pass2_widths.py` | Top-down width resolution |
| `src/smart_report/layout/pass3_heights.py` | Bottom-up height + local position calculation |
| `src/smart_report/layout/pass4_render.py` | Flatten layout tree into sorted `RenderItem` list |
| `src/smart_report/layout/paginate.py` | Auto-pagination logic; table-aware splitting |
| `src/smart_report/layout/table_model.py` | Table cell box model, column widths, header repeat logic |
| `src/smart_report/render/painters.py` | Registry mapping `node_type` → paint function |
| `src/smart_report/render/rl_adapter.py` | Thin adapter over ReportLab canvas |
| `src/smart_report/style/units.py` | Size parsing: `Fixed`, `Percent`, `Auto`, `resolve_size()` |
| `src/smart_report/style/color.py` | Color parsing to `RGBA` |
| `examples/` | Runnable demo scripts (generate `.pdf` files). `examples/zh_table_demo.py` is the Chinese-language table demo. |
| `tests/test_table_v2.py` | Unit tests for Table v2, including PDF-level regression tests that require `pypdf` (optional). |

---

## Coding Conventions

- `from __future__ import annotations` in every file.
- `@dataclass(slots=True)` or `@dataclass(frozen=True, slots=True)` for value types.
- Builder pattern: every method returns `self` (or the specific builder subclass) for chaining.
- Edge values (`margin`, `padding`, `cell_padding`) support both positional tuples and named keyword args. Prefer named args in examples.
- Sizes: points are the base unit. Strings like `"100%"`, `"auto"`, or numeric values are parsed by `style/units.py`.
- Page sizes: `"A4"` (595.2756 × 841.8898 pt) and `"LETTER"` (612 × 792 pt) are built-in.

---

## Common Pitfalls

- **`Document.save()` uses `importlib.import_module` inside the method** to resolve the 4 pass modules. Do not delete or rename `layout/pass2_widths.py`, `pass3_heights.py`, `pass4_render.py`, `paginate.py`, `render/painters.py`, `render/rl_adapter.py`, `style/units.py`, or `layout/node.py` without updating `_builder_core.py`.
- **Table pagination is complex.** `_split_table_node` in `paginate.py` clones table slices and must preserve `source_row_index` for cell styles to remain correct across pages. If you modify table splitting, run `tests/test_table_v2.py` — especially `TableV2PaginationTests`.
- **No formatter or linter is configured.** If you add one, update `pyproject.toml` and `pyrightconfig.json` accordingly.
- **Chinese docs live in `docs/zh/api.md`.** Keep them in sync if you change public API behavior.
- **`test_table_v2_qa.py` in the repo root** is a QA script (not part of the test suite) and is intentionally gitignored.

---

## Dependencies

Core runtime: `reportlab>=4.0.0`, `Pillow>=10.0.0`, `svglib>=1.5.1`.

Optional test dependency: `pypdf` (required for PDF-level regression tests in `test_table_v2.py`).
