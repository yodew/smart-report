"""Flow layout example for smart-report."""

from smart_report import Frame, document


def main() -> None:
    doc = document()
    page = doc.page("A4")

    frame = Frame().padding(32)
    frame.add_text("Flow Layout Demo").font_size(24).color("#0f172a").margin((0, 0, 16, 0))
    frame.add_text(
        "This page uses a flow container. Elements stack vertically, inherit the available width, "
        "and are measured before rendering."
    ).font_size(12).color("#334155").margin((0, 0, 12, 0))
    frame.add_spacer(12)
    frame.add_text("• Automatic vertical stacking").font_size(12).color("#1e293b")
    frame.add_text("• Text height measured from resolved width").font_size(12).color("#1e293b")
    frame.add_text("• Margins and padding influence local positions").font_size(12).color("#1e293b")

    page.add(frame)
    doc.save("examples/flow_layout.pdf")


if __name__ == "__main__":
    main()
