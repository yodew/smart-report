"""Generate a PDF showcasing v2.4 document structure: sections, overlays, metadata, and outlines."""

from __future__ import annotations

from smart_report import Table, document


def build_report() -> None:
    doc = document()
    doc.metadata(
        title="v2.4 Document Structure",
        author="smart-report",
        subject="Section templates, overlays, metadata, and outlines",
        keywords="sections, pagination, outlines, metadata",
    )

    doc.footer().height(24).add_text(
        "Global footer  Page {page_number}/{total_pages}"
    ).absolute(36, 6)

    cover = doc.section("Cover", page_numbering="restart", outline=True)
    cover_page = cover.page("A4")
    cover_frame = cover_page.add_frame().padding(36)
    cover_frame.add_text("v2.4 Document Structure").font_size(28).line_height(34).margin(bottom=16)
    cover_frame.add_text(
        "This cover page has no section-specific header or footer, "
        "so the global fallback footer appears below."
    ).font_size(12).line_height(16).margin(bottom=8)
    cover_frame.add_text(
        "Subsequent sections define their own overlays and demonstrate "
        "section page numbering, metadata, and automatic outlines."
    ).font_size(12).line_height(16)

    intro = doc.section("Introduction", page_numbering="restart", outline=True)
    intro.header().height(28).add_text(
        "Introduction  {section_page_number}/{section_total_pages}"
    ).absolute(36, 8)
    intro.footer().height(24).add_text(
        "Intro footer  {section_name} {section_page_number}/{section_total_pages}"
    ).absolute(36, 6)

    intro_page = intro.page("A4")
    intro_frame = intro_page.add_frame().padding(36)
    intro_frame.add_text("Introduction").font_size(22).line_height(28).margin(bottom=12)
    intro_frame.add_text(
        "This section demonstrates section-scoped overlays, "
        "section page placeholders, and automatic PDF outlines."
    ).font_size(11).line_height(16).margin(bottom=12)
    for index in range(6):
        intro_frame.add_text(
            f"Introduction paragraph {index + 1}. "
            "Content flows across pages to show section page numbering."
        ).font_size(11).line_height(15).margin(bottom=8)

    body = doc.section("Body", page_numbering="restart", outline=True)
    body.header().height(28).add_text(
        "Body section  {section_page_number}/{section_total_pages}"
    ).absolute(36, 8)
    body.footer().height(24).add_text(
        "Body footer  {section_name} {section_page_number}/{section_total_pages}"
    ).absolute(36, 6)

    body_page = body.page("A4")
    body_frame = body_page.add_frame().padding(36)
    body_frame.add_text("Body Content").font_size(22).line_height(28).margin(bottom=12)
    body_frame.add_text(
        "The body section carries its own header and footer templates, "
        "overriding the global fallback footer on its pages."
    ).font_size(11).line_height(16).margin(bottom=12)

    rows = [["Region", "Revenue", "Growth"]]
    for index in range(18):
        rows.append([f"Region {index + 1}", f"${(index + 1) * 200}K", f"+{(index % 7) + 2}%"])
    body_frame.add(
        Table(rows)
        .column_widths(["45%", "30%", "25%"])
        .align(["left", "right", "right"])
        .cell_padding(vertical=7, horizontal=9)
        .header(background="#0f172a", color="#ffffff", repeat=True)
        .zebra("#f8fafc")
        .font_size(10)
        .line_height(13)
        .color("#111827")
        .background("#ffffff")
        .stroke("#cbd5e1", 1)
        .margin((12, 0, 0, 0))
    )

    for index in range(12):
        body_frame.add_text(
            f"Body note {index + 1}. "
            "Additional content to push the table onto subsequent pages."
        ).font_size(11).line_height(15).margin(bottom=6)

    doc.save("examples/v2_4_document_structure.pdf")


if __name__ == "__main__":
    build_report()
