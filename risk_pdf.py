"""
risk_pdf.py
───────────
Generates the branded Risk Analysis PDF report for LexAI.

Usage:
    from reports.risk_pdf import generate_risk_pdf
    pdf_bytes = generate_risk_pdf(risks_list, doc_name="NDA.pdf", word_count=2350)
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# ── Brand palette (kept in sync with app.py's CSS) ─────────────────────────
NAVY     = colors.HexColor("#0F2137")
GREY     = colors.HexColor("#6B7280")
LGREY    = colors.HexColor("#F3F4F6")
BLUE_BG  = colors.HexColor("#EFF6FF")
BLUE_TX  = colors.HexColor("#1E3A5F")

LEVEL_COLORS = {
    "HIGH":   (colors.HexColor("#991B1B"), colors.HexColor("#FEE2E2")),
    "MEDIUM": (colors.HexColor("#92400E"), colors.HexColor("#FEF3C7")),
    "LOW":    (colors.HexColor("#065F46"), colors.HexColor("#D1FAE5")),
}
LEVEL_LABEL = {
    "HIGH":   "\u25CF HIGH RISK",
    "MEDIUM": "\u25CF MEDIUM RISK",
    "LOW":    "\u25CF LOW RISK",
}
RISK_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleNavy", parent=styles["Title"], textColor=NAVY,
                                 fontName="Helvetica-Bold", fontSize=20, spaceAfter=2),
        "sub": ParagraphStyle("Sub", parent=styles["Normal"], textColor=GREY,
                               fontSize=9, spaceAfter=14),
        "label": ParagraphStyle("Label", parent=styles["Normal"], textColor=GREY,
                                 fontName="Helvetica-Bold", fontSize=7.5, spaceAfter=2, leading=10),
        "clause": ParagraphStyle("Clause", parent=styles["Normal"], textColor=colors.HexColor("#374151"),
                                  fontName="Helvetica-Oblique", fontSize=9.5, leading=13),
        "body": ParagraphStyle("Body", parent=styles["Normal"], textColor=colors.HexColor("#374151"),
                                fontSize=9.5, leading=14),
        "suggestion": ParagraphStyle("Suggestion", parent=styles["Normal"], textColor=BLUE_TX,
                                      fontSize=9.5, leading=14),
        "footer": ParagraphStyle("Footer", parent=styles["Normal"], textColor=GREY, fontSize=7.5),
    }


def _summary_table(counts: dict) -> Table:
    table = Table(
        [["HIGH RISKS", "MEDIUM RISKS", "LOW RISKS"],
         [str(counts["HIGH"]), str(counts["MEDIUM"]), str(counts["LOW"])]],
        colWidths=[170, 170, 170],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("TEXTCOLOR", (0, 1), (0, 1), LEVEL_COLORS["HIGH"][0]),
        ("TEXTCOLOR", (1, 1), (1, 1), LEVEL_COLORS["MEDIUM"][0]),
        ("TEXTCOLOR", (2, 1), (2, 1), LEVEL_COLORS["LOW"][0]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _risk_card(risk: dict, index: int, styles: dict) -> Table:
    level = str(risk.get("risk_level", "LOW")).upper()
    if level not in LEVEL_COLORS:
        level = "LOW"
    text_color, bg_color = LEVEL_COLORS[level]
    clause     = risk.get("clause", "Not specified")
    why        = risk.get("why_its_a_risk", "")
    suggestion = risk.get("suggestion", "")

    badge_table = Table([[f"{index}.  {LEVEL_LABEL[level]}"]], colWidths=[510])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), text_color),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))

    clause_box = Table([[Paragraph(f"\u25A0 {clause}", styles["clause"])]], colWidths=[494])
    clause_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LGREY),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor("#9CA3AF")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))

    suggestion_box = Table([[Paragraph(f"<b>SUGGESTION</b><br/>{suggestion}", styles["suggestion"])]], colWidths=[494])
    suggestion_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor("#1E6FA5")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))

    card = Table([
        [badge_table],
        [Spacer(1, 6)],
        [Paragraph("FLAGGED CLAUSE", styles["label"])],
        [clause_box],
        [Spacer(1, 6)],
        [Paragraph("WHY IT'S A RISK", styles["label"])],
        [Paragraph(why, styles["body"])],
        [Spacer(1, 6)],
        [suggestion_box],
    ], colWidths=[510])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return card


def generate_risk_pdf(risks: list, doc_name: str, word_count: int) -> bytes:
    """
    Render the risk analysis as a branded PDF report.

    Args:
        risks: list of dicts with keys clause / risk_level / why_its_a_risk / suggestion
        doc_name: original filename, shown in the header
        word_count: word count of the analysed document, shown in the header

    Returns:
        Raw PDF bytes, ready for st.download_button or writing to disk.
    """
    styles = _build_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=22 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        title=f"Risk Report - {doc_name}",
    )

    story = [
        Paragraph("Legal Risk Analysis Report", styles["title"]),
        Paragraph(
            f"Document: {doc_name} &nbsp;&nbsp;|&nbsp;&nbsp; Words analysed: {word_count:,} "
            f"&nbsp;&nbsp;|&nbsp;&nbsp; Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}",
            styles["sub"]
        ),
    ]

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in risks:
        lvl = str(r.get("risk_level", "")).upper()
        if lvl in counts:
            counts[lvl] += 1
    story += [_summary_table(counts), Spacer(1, 16)]

    sorted_risks = sorted(risks, key=lambda r: RISK_ORDER.get(str(r.get("risk_level", "")).upper(), 3))
    for i, risk in enumerate(sorted_risks, 1):
        story += [_risk_card(risk, i, styles), Spacer(1, 12)]

    story += [
        Spacer(1, 10),
        Paragraph(
            "Generated by LexAI \u2014 Legal Document Analyser. This report is AI-generated and is not a "
            "substitute for advice from a qualified legal professional.",
            styles["footer"]
        ),
    ]

    doc.build(story)
    buf.seek(0)
    return buf.read()