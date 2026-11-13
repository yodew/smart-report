# Reviewed PDF page baselines

These RGB PNGs are rendered at 72 dpi with the locked PDFium dependency. The
`darwin/` and `linux/` directories each cover
every page of `examples.quality_reports.chinese_report()`,
`examples.quality_reports.rich_table_report()` and the four-page
`examples/yuanxi_text_effects.py` report. Fonts are bundled and licensed in `examples/fonts`.

The initial images were captured before the document orchestration extraction,
then the Chinese and table baselines were corrected after PDF-coordinate tests
demonstrated off-page footers and continuation content. The corrected pages must
show visible footers and body text within page padding. Yuanxi pages retain the
original typography and shadow appearance.

`tests/test_report_visuals.py` compares every page, and content/coordinate tests
independently detect lost text, missing links and off-page baselines. Run the full
suite with `SMART_REPORT_QA_DIR` set to retain the actual PDFs and PNGs, inspect them
at readable scale, and only replace a baseline for an intentional reviewed change.
There is no automatic baseline-update mode.

PDFium substitutes unembedded PDF base-14 fonts differently on Linux and macOS.
The first CI run demonstrated that Linux Python 3.10 and 3.14 produce byte-identical
PNGs, while rendering those same Linux-produced PDFs on macOS exactly matches the
macOS reference images. The differences are glyph rasterization, not page geometry.
Both platform references were inspected, and both retain the same 24/255 channel
threshold and 0.1% changed-channel budget. New platforms need reviewed references
before running this full visual suite; runtime PDF generation is unaffected.
