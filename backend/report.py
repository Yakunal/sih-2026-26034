"""
report.py — turns a saved inspection into a PDF compliance report.

Uses ReportLab's "platypus" layout engine: you build a list of flowables
(paragraphs, tables, images) called `story`, and ReportLab lays them out across
pages for you.

The visual style matches the web UI: flat colour blocks, no shadows, no
gradients, bold type for hierarchy.
"""

from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from compliance import load_rules
from models import InspectionDetail

import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("/tmp") if os.getenv("VERCEL") else BASE_DIR
REPORTS_DIR = DATA_DIR / "reports"
UPLOADS_DIR = DATA_DIR / "uploads"

# Same palette as the frontend design system.
BLUE = colors.HexColor("#3B82F6")
EMERALD = colors.HexColor("#10B981")
AMBER = colors.HexColor("#F59E0B")
DANGER = colors.HexColor("#EF4444")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#F3F4F6")
BORDER = colors.HexColor("#E5E7EB")

STATUS_COLOURS = {
    "COMPLIANT": EMERALD,
    "NEEDS_REVIEW": AMBER,
    "POTENTIAL_VIOLATION": DANGER,
}

STATUS_LABELS = {
    "COMPLIANT": "COMPLIANT",
    "NEEDS_REVIEW": "NEEDS REVIEW",
    "POTENTIAL_VIOLATION": "POTENTIAL VIOLATION",
}

RESULT_COLOURS = {"PASS": EMERALD, "FAIL": DANGER, "REVIEW": AMBER, "NOT_APPLICABLE": colors.HexColor("#9CA3AF")}

# Short labels: the result column is narrow, and "NOT APPLICABLE" wraps mid-word.
RESULT_LABELS = {"PASS": "PASS", "FAIL": "FAIL", "REVIEW": "REVIEW", "NOT_APPLICABLE": "N/A"}

# How the extraction fields are presented, in the order an inspector reads a label.
DECLARATION_ROWS = [
    ("Product name", "product_name"),
    ("Common / generic name", "common_generic_name"),
    ("Manufacturer", "manufacturer_name"),
    ("Manufacturer address", "manufacturer_address"),
    ("Packer", "packer_name"),
    ("Importer", "importer_name"),
    ("Net quantity", "net_quantity"),
    ("Retail sale price", "mrp"),
    ("Price line (as printed)", "mrp_text_verbatim"),
    ("Month and year", "date_of_packing"),
    ("Consumer care", "consumer_care"),
    ("Country of origin", "country_of_origin"),
]

SOURCE_LABELS = {
    "live_ai": "Live Gemini analysis of the uploaded image",
    "demo_cached": "DEMO — cached extraction, live rule engine (not a fresh AI analysis)",
    "seed": "SAMPLE DATA — generated for demonstration, not a real inspection",
}

DISCLAIMER = (
    "This prototype provides automated decision support and does not replace official "
    "inspection or legal determination. Findings are produced from a photograph by a "
    "subset of implemented checks; declarations printed on panels not visible in the "
    "image cannot be assessed."
)

# The standard PDF fonts have no rupee glyph, so it would render as a black box.
_REPLACEMENTS = {"₹": "Rs ", "—": "-", "–": "-", "‘": "'", "’": "'"}


def _safe(value) -> str:
    """Make a value printable by the built-in PDF fonts, and escape XML."""
    if value is None or value == "":
        return "Not detected"
    text = str(value)
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _readable_date(value: str) -> str:
    """Turn the stored ISO timestamp into something a person reads on a report."""
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y at %H:%M")
    except (TypeError, ValueError):
        return value


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------

_base = getSampleStyleSheet()

STYLES = {
    "title": ParagraphStyle("title", parent=_base["Normal"], fontName="Helvetica-Bold",
                            fontSize=19, leading=23, textColor=colors.white),
    "subtitle": ParagraphStyle("subtitle", parent=_base["Normal"], fontName="Helvetica",
                               fontSize=9, leading=12, textColor=colors.white),
    "h2": ParagraphStyle("h2", parent=_base["Normal"], fontName="Helvetica-Bold",
                         fontSize=12, leading=15, textColor=INK, spaceBefore=14, spaceAfter=6),
    "body": ParagraphStyle("body", parent=_base["Normal"], fontName="Helvetica",
                           fontSize=9, leading=13, textColor=INK),
    "small": ParagraphStyle("small", parent=_base["Normal"], fontName="Helvetica",
                            fontSize=7.5, leading=10, textColor=colors.HexColor("#6B7280")),
    "cell": ParagraphStyle("cell", parent=_base["Normal"], fontName="Helvetica",
                           fontSize=8.5, leading=11, textColor=INK),
    "cell_bold": ParagraphStyle("cell_bold", parent=_base["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, leading=11, textColor=INK),
    # Header cells need their own white style: a Paragraph carries its own colour,
    # so a TableStyle TEXTCOLOR command cannot override it.
    "cell_head": ParagraphStyle("cell_head", parent=_base["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, leading=11, textColor=colors.white),
    "status": ParagraphStyle("status", parent=_base["Normal"], fontName="Helvetica-Bold",
                             fontSize=22, leading=26, textColor=colors.white),
    "score": ParagraphStyle("score", parent=_base["Normal"], fontName="Helvetica-Bold",
                            fontSize=22, leading=26, textColor=colors.white, alignment=TA_CENTER),
}

CONTENT_WIDTH = A4[0] - 32 * mm


def _colour_band(cells, background, padding=10):
    """A flat solid-colour block — the report's main structural device."""
    table = Table(cells, colWidths=[CONTENT_WIDTH * 0.72, CONTENT_WIDTH * 0.28])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return table


def _data_table(rows, col_widths, header=True):
    """A plain table: thin borders, grey header, zebra striping. No shadows."""
    table = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ]
        for index in range(2, len(rows), 2):
            style.append(("BACKGROUND", (0, index), (-1, index), MUTED))
    table.setStyle(TableStyle(style))
    return table


def _fitted_image(filename: str, max_width: float, max_height: float) -> Image | None:
    """Scale an uploaded image to fit the page without distorting it."""
    path = UPLOADS_DIR / filename
    if not path.exists():
        return None
    try:
        with PILImage.open(path) as opened:
            width, height = opened.size
    except Exception:
        return None

    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def generate_report(inspection: InspectionDetail) -> Path:
    """Build the PDF for one inspection and return the path to the file."""
    REPORTS_DIR.mkdir(exist_ok=True)
    output_path = REPORTS_DIR / f"inspection_{inspection.id}.pdf"

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Compliance Report #{inspection.id}",
        author="Legal Metrology Compliance Checker (prototype)",
    )

    compliance = inspection.compliance
    story = []

    # --- Title band -------------------------------------------------------
    story.append(_colour_band([[
        [Paragraph("LEGAL METROLOGY COMPLIANCE REPORT", STYLES["title"]),
         Spacer(1, 3),
         Paragraph("Packaged Commodities Rules, 2011 &mdash; automated pre-screening", STYLES["subtitle"])],
        Paragraph(f"Report<br/>#{inspection.id}", STYLES["subtitle"]),
    ]], BLUE, padding=12))
    story.append(Spacer(1, 10))

    # --- What was inspected ----------------------------------------------
    story.append(_data_table(
        [
            [Paragraph("Product", STYLES["cell_bold"]), Paragraph(_safe(inspection.product_name), STYLES["cell"])],
            [Paragraph("Manufacturer", STYLES["cell_bold"]), Paragraph(_safe(inspection.manufacturer), STYLES["cell"])],
            [Paragraph("Inspection date", STYLES["cell_bold"]), Paragraph(_readable_date(inspection.scan_date), STYLES["cell"])],
            [Paragraph("Extraction source", STYLES["cell_bold"]),
             Paragraph(_safe(SOURCE_LABELS.get(inspection.source, inspection.source)), STYLES["cell"])],
            [Paragraph("AI model", STYLES["cell_bold"]),
             Paragraph(_safe(inspection.model_used or "Not used (cached extraction)"), STYLES["cell"])],
        ],
        [CONTENT_WIDTH * 0.28, CONTENT_WIDTH * 0.72],
        header=False,
    ))
    story.append(Spacer(1, 12))

    # --- Verdict band -----------------------------------------------------
    status_colour = STATUS_COLOURS.get(compliance.status, AMBER)
    story.append(_colour_band([[
        [Paragraph("OVERALL STATUS", STYLES["subtitle"]),
         Paragraph(STATUS_LABELS.get(compliance.status, compliance.status), STYLES["status"])],
        [Paragraph("COMPLIANCE SCORE", ParagraphStyle("c", parent=STYLES["subtitle"], alignment=TA_CENTER)),
         Paragraph(f"{compliance.score}/100", STYLES["score"])],
    ]], status_colour, padding=12))
    story.append(Spacer(1, 8))
    story.append(Paragraph(_safe(compliance.status_reason), STYLES["body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"{compliance.passed} checks passed &nbsp;|&nbsp; {compliance.failed} failed &nbsp;|&nbsp; "
        f"{compliance.review} need physical verification &nbsp;|&nbsp; "
        f"{compliance.not_applicable} not applicable",
        STYLES["small"],
    ))

    # --- Optional AI explanation -----------------------------------------
    if inspection.explanation:
        story.append(Paragraph("Summary", STYLES["h2"]))
        story.append(Paragraph(_safe(inspection.explanation), STYLES["body"]))
        story.append(Spacer(1, 2))
        story.append(Paragraph(
            "Generated by the AI from the rule engine's findings above. The findings themselves "
            "are produced by the rule engine, not by the AI.", STYLES["small"]))

    # --- Detected declarations -------------------------------------------
    story.append(Paragraph("Declarations detected on the label", STYLES["h2"]))
    rows = [[Paragraph("Declaration", STYLES["cell_head"]),
             Paragraph("Value read from the image", STYLES["cell_head"]),
             Paragraph("Detected", STYLES["cell_head"])]]
    extracted = inspection.extracted.model_dump()
    for label, field in DECLARATION_ROWS:
        value = extracted.get(field)
        rows.append([
            Paragraph(label, STYLES["cell"]),
            Paragraph(_safe(value), STYLES["cell"]),
            Paragraph("Yes" if value else "No", STYLES["cell_bold"]),
        ])
    table = _data_table(rows, [CONTENT_WIDTH * 0.26, CONTENT_WIDTH * 0.58, CONTENT_WIDTH * 0.16])
    for index, (_, field) in enumerate(DECLARATION_ROWS, start=1):
        colour = EMERALD if extracted.get(field) else colors.HexColor("#9CA3AF")
        table.setStyle(TableStyle([("TEXTCOLOR", (2, index), (2, index), colour)]))
    story.append(table)
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        f"Image quality reported by the extraction step: {_safe(inspection.extracted.image_quality)}. "
        f"Extraction confidence: "
        f"{inspection.extracted.overall_confidence if inspection.extracted.overall_confidence is not None else 'not reported'}.",
        STYLES["small"]))

    # --- Rule-by-rule results --------------------------------------------
    story.append(Paragraph("Rule checks", STYLES["h2"]))
    rows = [[Paragraph("Rule", STYLES["cell_head"]),
             Paragraph("Reference", STYLES["cell_head"]),
             Paragraph("Requirement checked", STYLES["cell_head"]),
             Paragraph("Result", STYLES["cell_head"]),
             Paragraph("Basis", STYLES["cell_head"])]]
    for check in compliance.checks:
        rows.append([
            Paragraph(check.rule_id, STYLES["cell_bold"]),
            Paragraph(_safe(check.rule_reference), STYLES["cell"]),
            Paragraph(_safe(check.name), STYLES["cell"]),
            Paragraph(RESULT_LABELS.get(check.result, check.result), STYLES["cell_bold"]),
            Paragraph(_safe(check.reason), STYLES["cell"]),
        ])
    table = _data_table(
        rows,
        [CONTENT_WIDTH * 0.08, CONTENT_WIDTH * 0.13, CONTENT_WIDTH * 0.25,
         CONTENT_WIDTH * 0.13, CONTENT_WIDTH * 0.41],
    )
    for index, check in enumerate(compliance.checks, start=1):
        table.setStyle(TableStyle([
            ("TEXTCOLOR", (3, index), (3, index), RESULT_COLOURS.get(check.result, INK)),
        ]))
    story.append(table)

    # --- Product image ----------------------------------------------------
    if inspection.image_url:
        story.append(PageBreak())
        story.append(Paragraph("Image inspected", STYLES["h2"]))
        image = _fitted_image(Path(inspection.image_url).name, CONTENT_WIDTH, 170 * mm)
        if image:
            story.append(image)
        else:
            story.append(Paragraph("The image file is no longer available.", STYLES["body"]))

    # --- Rule references --------------------------------------------------
    story.append(Paragraph("Implemented rules and their sources", STYLES["h2"]))
    rows = [[Paragraph("Rule", STYLES["cell_head"]),
             Paragraph("Reference", STYLES["cell_head"]),
             Paragraph("Requirement", STYLES["cell_head"]),
             Paragraph("Type", STYLES["cell_head"])]]
    unverified = 0
    for rule in load_rules():
        if not rule["citation_verified"]:
            unverified += 1
        rows.append([
            Paragraph(rule["id"], STYLES["cell_bold"]),
            Paragraph(_safe(rule["rule_reference"]) + ("" if rule["citation_verified"] else " *"), STYLES["cell"]),
            Paragraph(_safe(rule["requirement"]), STYLES["cell"]),
            Paragraph(rule["check"].replace("_", " "), STYLES["cell"]),
        ])
    story.append(_data_table(
        rows,
        [CONTENT_WIDTH * 0.08, CONTENT_WIDTH * 0.17, CONTENT_WIDTH * 0.62, CONTENT_WIDTH * 0.13],
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "All references are to the Legal Metrology (Packaged Commodities) Rules, 2011."
        + (f" * {unverified} citation(s) have not yet been cross-checked against the official "
           f"gazette text and are marked accordingly." if unverified else ""),
        STYLES["small"]))

    # --- Disclaimer -------------------------------------------------------
    story.append(Spacer(1, 12))
    disclaimer = Table([[Paragraph(f"<b>Disclaimer.</b> {DISCLAIMER}", STYLES["small"])]], colWidths=[CONTENT_WIDTH])
    disclaimer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MUTED),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(disclaimer))

    document.build(story)
    return output_path
