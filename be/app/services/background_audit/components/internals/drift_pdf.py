"""PDF generation for weight drift analysis via reportlab."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_drift_pdf(pattern_card: dict[str, Any]) -> bytes:
    """Render drift analysis as a PDF. Returns raw bytes."""
    drift = pattern_card.get("drift_data", {})
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DriftTitle", parent=styles["Title"], fontSize=16)
    heading = ParagraphStyle("DriftH2", parent=styles["Heading2"], fontSize=12)
    body = styles["BodyText"]

    elements: list = []
    elements.append(Paragraph("Weight Drift Analysis Report", title_style))
    elements.append(Spacer(1, 6 * mm))

    narrative = pattern_card.get("plain_language", "No narrative available.")
    elements.append(Paragraph(narrative, body))
    elements.append(Spacer(1, 4 * mm))

    _add_indicator_table(elements, drift.get("indicators", []), heading)
    _add_outlier_section(elements, drift.get("outliers", []), heading, body)
    _add_countermeasures(elements, drift.get("countermeasures", []), heading, body)

    doc.build(elements)
    return buf.getvalue()


def _add_indicator_table(elements: list, indicators: list, heading: Any) -> None:
    if not indicators:
        return
    elements.append(Paragraph("Indicator Statistics", heading))
    elements.append(Spacer(1, 2 * mm))

    header = ["Indicator", "Mean", "Median", "Std", "Min", "Max", "Trend"]
    rows = [header]
    for ind in indicators:
        rows.append([
            str(ind.get("name", "")),
            str(ind.get("mean", "")),
            str(ind.get("median", "")),
            str(ind.get("std", "")),
            str(ind.get("min_val", "")),
            str(ind.get("max_val", "")),
            str(ind.get("trend", "")),
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 4 * mm))


def _add_outlier_section(elements: list, outliers: list, heading: Any, body: Any) -> None:
    if not outliers:
        return
    elements.append(Paragraph(f"Outlier Customers ({len(outliers)})", heading))
    elements.append(Spacer(1, 2 * mm))

    header = ["Customer ID", "Indicator", "Multiplier", "Deviation"]
    rows = [header]
    for o in outliers[:20]:
        rows.append([
            str(o.get("customer_id", ""))[:12],
            str(o.get("indicator_name", "")),
            str(o.get("multiplier", "")),
            str(o.get("deviation", "")),
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E67E22")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 4 * mm))


def _add_countermeasures(elements: list, countermeasures: list, heading: Any, body: Any) -> None:
    if not countermeasures:
        return
    elements.append(Paragraph("Recommended Countermeasures", heading))
    elements.append(Spacer(1, 2 * mm))

    for cm in countermeasures:
        severity = cm.get("severity", "medium").upper()
        text = (
            f"<b>[{severity}] {cm.get('indicator_name', '')}</b>: "
            f"{cm.get('issue', '')} — <i>{cm.get('suggestion', '')}</i>"
        )
        elements.append(Paragraph(text, body))
        elements.append(Spacer(1, 1.5 * mm))
