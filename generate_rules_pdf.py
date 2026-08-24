import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont('Helvetica-Bold', 7)
        self.setFillColor(colors.HexColor('#6B7280'))
        
        # Running Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(15 * mm, 285 * mm, 'LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011 — 15 RULES & SCORING ENGINE ARCHITECTURE')
            self.drawRightString(195 * mm, 285 * mm, 'SIH-26034')
            self.setStrokeColor(colors.HexColor('#CBD5E1'))
            self.setLineWidth(0.5)
            self.line(15 * mm, 282 * mm, 195 * mm, 282 * mm)
            
        # Running Footer (All pages)
        self.setStrokeColor(colors.HexColor('#CBD5E1'))
        self.setLineWidth(0.5)
        self.line(15 * mm, 14 * mm, 195 * mm, 14 * mm)
        self.setFont('Helvetica', 8)
        self.drawString(15 * mm, 9 * mm, 'Automated Packaged Commodity Compliance Verification System | Confidential Technical Guide')
        page_str = f'Page {self._pageNumber} of {page_count}'
        self.drawRightString(195 * mm, 9 * mm, page_str)
        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    NAVY = colors.HexColor('#0F172A')       # Slate 900
    PRIMARY = colors.HexColor('#1E3A8A')    # Blue 900
    ACCENT_BLUE = colors.HexColor('#2563EB')# Blue 600
    EMERALD = colors.HexColor('#047857')    # Emerald 700
    AMBER = colors.HexColor('#B45309')      # Amber 700
    RED = colors.HexColor('#B91C1C')        # Red 700
    DARK = colors.HexColor('#1E293B')       # Slate 800
    MUTED = colors.HexColor('#475569')      # Slate 600
    BG_LIGHT = colors.HexColor('#F8FAFC')   # Slate 50
    BORDER_COLOR = colors.HexColor('#E2E8F0')# Slate 200

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.white,
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#93C5FD'),
        alignment=0,
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=NAVY,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.5,
        textColor=DARK,
        spaceAfter=4,
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7.4,
        leading=10,
        textColor=DARK,
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7.4,
        leading=10,
        textColor=DARK,
    )
    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        fontName='Helvetica',
        fontSize=7.4,
        leading=10,
        textColor=DARK,
        alignment=1,
    )
    badge_pass = ParagraphStyle(
        'BadgePass',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9,
        textColor=EMERALD,
        alignment=1,
    )
    badge_fail = ParagraphStyle(
        'BadgeFail',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9,
        textColor=RED,
        alignment=1,
    )
    badge_review = ParagraphStyle(
        'BadgeReview',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9,
        textColor=AMBER,
        alignment=1,
    )

    story = []

    # -------------------------------------------------------------------------
    # DOCUMENT HERO BANNER
    # -------------------------------------------------------------------------
    banner_data = [
        [
            Paragraph('LEGAL METROLOGY (PACKAGED COMMODITIES) RULES, 2011', subtitle_style),
            Paragraph('SIH-26034 SPECIFICATION', ParagraphStyle('MetaRight', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.HexColor('#93C5FD'), alignment=2))
        ],
        [
            Paragraph('15 Statutory Rules & Deterministic Scoring Engine Architecture', title_style),
            ''
        ],
        [
            Paragraph('Comprehensive Guide to Label Verification, Rule Classification, Mathematical Scoring (0–100), and Defensibility', subtitle_style),
            Paragraph('ENGINE: v1.0 Production', ParagraphStyle('MetaRight2', fontName='Helvetica', fontSize=7.5, leading=9, textColor=colors.HexColor('#CBD5E1'), alignment=2))
        ]
    ]
    banner_table = Table(banner_data, colWidths=[130 * mm, 50 * mm])
    banner_table.setStyle(TableStyle([
        ('SPAN', (0, 1), (1, 1)),
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # EXECUTIVE SUMMARY: THE 2-STAGE SEPARATION
    # -------------------------------------------------------------------------
    story.append(Paragraph('1. Executive Architecture: The 2-Stage Pipeline', h1_style))
    story.append(Paragraph(
        'The foundational engineering decision of this compliance platform is the <b>strict separation</b> between '
        'Multimodal Vision AI (OCR) and Statutory Legal Judgment. Large Language Models should never directly declare whether '
        'a product is legally compliant, because neural networks exhibit stochastic output drift, hallucinate absent text, and '
        'cannot be defended in official audits. Our platform divides the task into two distinct, auditable stages:',
        body_style
    ))

    pipeline_data = [
        [
            Paragraph('<b>STAGE 1: Vision OCR & Transcription</b><br/><i>(Google Gemini Multimodal API, Temperature = 0)</i>', table_cell_bold),
            Paragraph('<b>STAGE 2: Deterministic Rule Engine</b><br/><i>(Pure Python 3, Zero AI, Zero Randomness)</i>', table_cell_bold)
        ],
        [
            Paragraph(
                '• <b>Sole Objective:</b> Answer <i>\"What text is printed on this package?\"</i><br/>'
                '• Strictly limited to transcription of 12 declaration fields.<br/>'
                '• Governed by negative prompt constraints (never infer, guess, or invent).<br/>'
                '• Output validated against strict Pydantic JSON schema.<br/>'
                '• <b>Forbidden from making legal compliance determinations.</b>',
                table_cell_style
            ),
            Paragraph(
                '• <b>Sole Objective:</b> Answer <i>\"Does that text satisfy statutory rules?\"</i><br/>'
                '• Evaluates 15 codified rules from the 2011 Gazette notification.<br/>'
                '• Executes deterministic regex pattern matching & presence logic.<br/>'
                '• Computes weighted compliance score out of 100.<br/>'
                '• <b>100% reproducible: the same text always produces the exact same verdict.</b>',
                table_cell_style
            )
        ]
    ]
    pipeline_table = Table(pipeline_data, colWidths=[90 * mm, 90 * mm])
    pipeline_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F0FDF4')),
        ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(pipeline_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # SECTION 2: THE MATHEMATICAL SCORING ENGINE
    # -------------------------------------------------------------------------
    story.append(Paragraph('2. Mathematical Scoring Engine (How Products are Scored Out of 100)', h1_style))
    story.append(Paragraph(
        'The compliance score is not an arbitrary estimate. It is an exact <b>statutory ratio</b> calculated '
        'from the weight of legal declarations that passed against the total weight of declarations that could be evaluated:',
        body_style
    ))

    # Formula Box
    formula_data = [
        [
            Paragraph(
                '<font size=9.5 color="#1E3A8A"><b>THE COMPLIANCE SCORING FORMULA</b></font><br/><br/>'
                '<b>Compliance Score = round [ 100 × ( ∑ Passed Rule Weights ) / ( ∑ Scoreable Rule Weights ) ]</b><br/><br/>'
                'Where <i>Scoreable Rules</i> = All rules yielding <b>PASS</b> or <b>FAIL</b>.<br/>'
                'Rules yielding <b>REVIEW</b> (manual physical checks) or <b>NOT_APPLICABLE</b> are strictly excluded from both numerator and denominator.',
                ParagraphStyle('FormulaStyle', fontName='Helvetica', fontSize=8, leading=11, textColor=DARK, alignment=1)
            )
        ]
    ]
    formula_table = Table(formula_data, colWidths=[180 * mm])
    formula_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, PRIMARY),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(formula_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph('Key Principles Governing the Scoring Formula:', h2_style))
    principles_text = (
        '• <b>Weight Distribution:</b> Mandatory presence rules carry a weight of <b>2 points</b> each (omitting a mandatory '
        'declaration violates the core act), while format and conditional rules carry a weight of <b>1 point</b> each.<br/>'
        '• <b>Unbiased Exclusions:</b> Physical verification items (e.g. Rule 9 letter height) cannot be measured from a 2D smartphone photo. '
        'Instead of fabricating numbers, they receive <i>REVIEW</i> (weight 0) and are excluded from the score. A package is never penalized for what an image cannot answer.<br/>'
        '• <b>Double-Penalty Prevention:</b> If a declaration is missing entirely (e.g. no MRP on label), it receives <i>FAIL</i> under the '
        'presence check (LM006, losing 2 points). However, its corresponding format check (LM008) automatically evaluates to '
        '<i>NOT_APPLICABLE</i> rather than a second <i>FAIL</i>. This prevents one missing declaration from deducting double points.'
    )
    story.append(Paragraph(principles_text, body_style))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # SECTION 3: THE 4 CHECK CATEGORIES
    # -------------------------------------------------------------------------
    story.append(Paragraph('3. The 4 Check Categories (Mechanisms of Verification)', h1_style))
    story.append(Paragraph(
        'Every statutory rule belongs to one of four check types handled by dedicated verification subroutines:',
        body_style
    ))

    check_types_data = [
        [
            Paragraph('Check Type', table_header_style),
            Paragraph('Rules Count', table_header_style),
            Paragraph('Weight', table_header_style),
            Paragraph('Evaluation Mechanism & Statutory Handling', table_header_style)
        ],
        [
            Paragraph('<b>presence</b>', table_cell_bold),
            Paragraph('7 Rules<br/>(LM001–LM007)', table_cell_center),
            Paragraph('<b>2</b> each', table_cell_center),
            Paragraph(
                'Inspects whether mandatory statutory text is present. Supports legal alternative keys via '
                '<i>alt_fields</i> (e.g., LM001 accepts manufacturer name, packer name, OR importer name). '
                'Yields <b>PASS</b> if text is found; yields <b>FAIL</b> if null.',
                table_cell_style
            )
        ],
        [
            Paragraph('<b>format</b>', table_cell_bold),
            Paragraph('4 Rules<br/>(LM008–LM011)', table_cell_center),
            Paragraph('<b>1</b> each', table_cell_center),
            Paragraph(
                'Executes statutory regular expressions against detected text. If the field is missing, returns '
                '<b>NOT_APPLICABLE</b> (prevents double penalty). If present and compliant with prescribed gazette syntax, '
                'returns <b>PASS</b>; if non-compliant (e.g. "100 gms"), returns <b>FAIL</b> with escalation.',
                table_cell_style
            )
        ],
        [
            Paragraph('<b>conditional_<br/>presence</b>', table_cell_bold),
            Paragraph('1 Rule<br/>(LM012)', table_cell_center),
            Paragraph('<b>1</b>', table_cell_center),
            Paragraph(
                'Evaluates rules that apply only under specific trigger conditions. For imported commodities (LM012), '
                'the check is <b>NOT_APPLICABLE</b> unless an importer name is detected. Once an importer is named, '
                'Country of Origin becomes strictly mandatory.',
                table_cell_style
            )
        ],
        [
            Paragraph('<b>manual</b>', table_cell_bold),
            Paragraph('3 Rules<br/>(LM013–LM015)', table_cell_center),
            Paragraph('<b>0</b><br/>(Unscored)', table_cell_center),
            Paragraph(
                'Covers physical package properties that require millimeter calipers or schedule classification (Rule 9 letter height, '
                'display prominence, pack sizes). <b>Always returns REVIEW</b>. Never guesses numbers, maintaining legal integrity.',
                table_cell_style
            )
        ]
    ]
    check_table = Table(check_types_data, colWidths=[26 * mm, 22 * mm, 18 * mm, 114 * mm])
    check_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(check_table)
    story.append(Spacer(1, 8))

    # Page Break for Master Rule Catalog
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # SECTION 4: MASTER CATALOG OF ALL 15 IMPLEMENTED RULES
    # -------------------------------------------------------------------------
    story.append(Paragraph('4. Master Catalog of All 15 Implemented Rules', h1_style))
    story.append(Paragraph(
        'The table below presents all 15 rules codified in the compliance engine according to the Legal Metrology (Packaged Commodities) Rules, 2011:',
        body_style
    ))

    rules_table_data = [
        [
            Paragraph('ID', table_header_style),
            Paragraph('Gazette Ref', table_header_style),
            Paragraph('Statutory Requirement & Legal Scope', table_header_style),
            Paragraph('Check Type', table_header_style),
            Paragraph('Wt.', table_header_style),
            Paragraph('Escalates?', table_header_style)
        ],
        # LM001
        [
            Paragraph('<b>LM001</b>', table_cell_bold),
            Paragraph('Rule 6(1)(a)', table_cell_style),
            Paragraph('<b>Manufacturer / Packer / Importer Name:</b> Must declare name of manufacturer, packer, or importer.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM002
        [
            Paragraph('<b>LM002</b>', table_cell_bold),
            Paragraph('Rule 6(1)(a)', table_cell_style),
            Paragraph('<b>Complete Address:</b> Declaration must include complete physical address, not only a company name.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM003
        [
            Paragraph('<b>LM003</b>', table_cell_bold),
            Paragraph('Rule 6(1)(b)', table_cell_style),
            Paragraph('<b>Generic Name of Commodity:</b> Must state common or generic name (what product is, not just brand).', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM004
        [
            Paragraph('<b>LM004</b>', table_cell_bold),
            Paragraph('Rule 6(1)(c)', table_cell_style),
            Paragraph('<b>Net Quantity Declaration:</b> Must state net quantity in terms of standard metric weight/measure/count.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM005
        [
            Paragraph('<b>LM005</b>', table_cell_bold),
            Paragraph('Rule 6(1)(d)', table_cell_style),
            Paragraph('<b>Date of Manufacture / Packing:</b> Must declare month and year of manufacture, pre-packing, or import.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM006
        [
            Paragraph('<b>LM006</b>', table_cell_bold),
            Paragraph('Rule 6(1)(e)', table_cell_style),
            Paragraph('<b>Retail Sale Price (MRP):</b> Must declare the maximum retail sale price of the package.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM007
        [
            Paragraph('<b>LM007</b>', table_cell_bold),
            Paragraph('Rule 6(1)', table_cell_style),
            Paragraph('<b>Consumer Care Details:</b> Must state contact details for consumer complaints.', table_cell_style),
            Paragraph('presence', table_cell_center),
            Paragraph('2', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM008
        [
            Paragraph('<b>LM008</b>', table_cell_bold),
            Paragraph('Rule 6(1)(e)', table_cell_style),
            Paragraph('<b>MRP Inclusive of All Taxes:</b> Price must include prescribed wording <i>"inclusive of all taxes"</i>.', table_cell_style),
            Paragraph('format', table_cell_center),
            Paragraph('1', table_cell_center),
            Paragraph('<b>Yes</b>', badge_fail)
        ],
        # LM009
        [
            Paragraph('<b>LM009</b>', table_cell_bold),
            Paragraph('Rule 8', table_cell_style),
            Paragraph('<b>Standard Metric Unit Symbol:</b> Net quantity must use prescribed symbols (g, kg, ml, l). Rejects <i>"gms", "gm", "ltr"</i>.', table_cell_style),
            Paragraph('format', table_cell_center),
            Paragraph('1', table_cell_center),
            Paragraph('<b>Yes</b>', badge_fail)
        ],
        # LM010
        [
            Paragraph('<b>LM010</b>', table_cell_bold),
            Paragraph('Rule 6(1)(d)', table_cell_style),
            Paragraph('<b>Readable Month & Year:</b> Date must identify valid month & year (e.g. 06/2026, JUN 2026). Rejects bare <i>"2026"</i>.', table_cell_style),
            Paragraph('format', table_cell_center),
            Paragraph('1', table_cell_center),
            Paragraph('<b>Yes</b>', badge_fail)
        ],
        # LM011
        [
            Paragraph('<b>LM011</b>', table_cell_bold),
            Paragraph('Rule 6(1)', table_cell_style),
            Paragraph('<b>Consumer Care Contact Route:</b> Must include actionable telephone number or email address, not only a department.', table_cell_style),
            Paragraph('format', table_cell_center),
            Paragraph('1', table_cell_center),
            Paragraph('<b>Yes</b>', badge_fail)
        ],
        # LM012
        [
            Paragraph('<b>LM012</b>', table_cell_bold),
            Paragraph('Rule 6', table_cell_style),
            Paragraph('<b>Country of Origin on Imports:</b> Mandated when an importer is declared. If domestic, evaluated as Not Applicable.', table_cell_style),
            Paragraph('conditional', table_cell_center),
            Paragraph('1', table_cell_center),
            Paragraph('<b>Yes</b>', badge_fail)
        ],
        # LM013
        [
            Paragraph('<b>LM013</b>', table_cell_bold),
            Paragraph('Rule 9 & Sch. II', table_cell_style),
            Paragraph('<b>Letter & Numeral Height:</b> Prescribes minimum physical millimeter font height based on PDP area. Requires physical check.', table_cell_style),
            Paragraph('manual', table_cell_center),
            Paragraph('0', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM014
        [
            Paragraph('<b>LM014</b>', table_cell_bold),
            Paragraph('Rule 7', table_cell_style),
            Paragraph('<b>Principal Display Panel Prominence:</b> Declarations must be conspicuous and grouped on the display panel.', table_cell_style),
            Paragraph('manual', table_cell_center),
            Paragraph('0', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
        # LM015
        [
            Paragraph('<b>LM015</b>', table_cell_bold),
            Paragraph('Second Schedule', table_cell_style),
            Paragraph('<b>Permitted Standard Pack Sizes:</b> Certain commodities must be sold only in prescribed schedule quantities.', table_cell_style),
            Paragraph('manual', table_cell_center),
            Paragraph('0', table_cell_center),
            Paragraph('No', table_cell_center)
        ],
    ]
    rules_table = Table(rules_table_data, colWidths=[15 * mm, 24 * mm, 86 * mm, 21 * mm, 12 * mm, 22 * mm])
    rules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(rules_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------------------
    # SECTION 5: THE 3 LEGAL VERDICTS & DECISION TREE
    # -------------------------------------------------------------------------
    story.append(Paragraph('5. The 3 Legal Verdicts & The Escalation Tree', h1_style))
    story.append(Paragraph(
        'The engine classifies every inspection into one of three statutory verdicts based on a defensible decision hierarchy:',
        body_style
    ))

    verdicts_data = [
        [
            Paragraph('Verdict', table_header_style),
            Paragraph('Statutory Meaning & Trigger Conditions', table_header_style),
            Paragraph('Legal Rationale & Defense', table_header_style)
        ],
        [
            Paragraph('<b>COMPLIANT</b>', badge_pass),
            Paragraph(
                '• All scoreable presence and format rules evaluated to <b>PASS</b>.<br/>'
                '• Image quality is verified as good and all text is legible.<br/>'
                '• Score = <b>100 / 100</b>.',
                table_cell_style
            ),
            Paragraph(
                'The product satisfies all automatically verifiable requirements under the 2011 Rules. '
                'Manual physical verification items (LM013–LM015) are noted for physical audit.',
                table_cell_style
            )
        ],
        [
            Paragraph('<b>NEEDS_REVIEW</b>', badge_review),
            Paragraph(
                '• <b>1 or 2 mandatory declarations missing</b> (absence of evidence).<br/>'
                '• <i>OR</i> photo is marked <b>blurry</b> or <b>partial</b>.<br/>'
                '• Typical Score: <b>88 / 100</b>.',
                table_cell_style
            ),
            Paragraph(
                '<b>Absence of evidence is not evidence of a defect.</b> A smartphone photo only captures 1 or 2 faces. '
                'Missing declarations might be printed on unphotographed panels. The system flags this for officer review '
                'rather than falsely declaring a legal violation.',
                table_cell_style
            )
        ],
        [
            Paragraph('<b>POTENTIAL_<br/>VIOLATION</b>', badge_fail),
            Paragraph(
                '• <b>A visible defect is detected</b> (e.g. "100 gms", missing tax wording on MRP, bad date).<br/>'
                '• <i>OR</i> <b>≥ 3 mandatory declarations are missing simultaneously</b>.<br/>'
                '• Typical Score: <b>≤ 71 / 100</b>.',
                table_cell_style
            ),
            Paragraph(
                'When an illegal format is visibly printed on the package, photographic proof of a statutory violation exists. '
                'Similarly, when 3+ mandatory items are absent, an incomplete label is statistically far more probable than an incomplete photo.',
                table_cell_style
            )
        ]
    ]
    verdicts_table = Table(verdicts_data, colWidths=[32 * mm, 74 * mm, 74 * mm])
    verdicts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(verdicts_table)
    story.append(Spacer(1, 8))

    # Page Break for Worked Examples
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # SECTION 6: WORKED SCORING EXAMPLES
    # -------------------------------------------------------------------------
    story.append(Paragraph('6. Worked Demonstration Cases & Mathematical Walkthroughs', h1_style))
    story.append(Paragraph(
        'The following four real-world scenarios illustrate exactly how weights are summed and scores are derived across diverse label conditions:',
        body_style
    ))

    examples_data = [
        [
            Paragraph('Scenario / Sample Product', table_header_style),
            Paragraph('Engine Findings & Rule Results', table_header_style),
            Paragraph('Mathematical Calculation', table_header_style),
            Paragraph('Final Verdict', table_header_style)
        ],
        # Example 1
        [
            Paragraph('<b>Example 1: Fully Compliant Product</b><br/><i>(Krisp Gold Biscuit, 200g)</i>', table_cell_bold),
            Paragraph(
                '• All 7 presence rules: <b>PASS</b> (14 pts)<br/>'
                '• All 4 format rules: <b>PASS</b> (4 pts)<br/>'
                '• Conditional origin: <b>NOT_APPLICABLE</b> (Domestic)<br/>'
                '• 3 Manual rules: <b>REVIEW</b> (Excluded)',
                table_cell_style
            ),
            Paragraph(
                'Passed Weight = 14 + 4 = 18<br/>'
                'Scoreable Weight = 18<br/>'
                '<b>Score = 100 × (18 / 18) = 100</b>',
                table_cell_style
            ),
            Paragraph('<b>COMPLIANT</b><br/>(Score: 100)', badge_pass)
        ],
        # Example 2
        [
            Paragraph('<b>Example 2: Missing MRP Declaration</b><br/><i>(Daily Choice Basmati, 1kg)</i>', table_cell_bold),
            Paragraph(
                '• 6 presence rules: <b>PASS</b> (12 pts)<br/>'
                '• LM006 (MRP presence): <b>FAIL</b> (0 / 2 pts)<br/>'
                '• LM008 (MRP format): <b>NOT_APPLICABLE</b> (Double penalty prevented)<br/>'
                '• 3 format rules: <b>PASS</b> (3 pts)',
                table_cell_style
            ),
            Paragraph(
                'Passed Weight = 12 + 3 = 15<br/>'
                'Scoreable Weight = 15 + 2 = 17<br/>'
                '<b>Score = 100 × (15 / 17) = 88</b>',
                table_cell_style
            ),
            Paragraph('<b>NEEDS_REVIEW</b><br/>(Score: 88)', badge_review)
        ],
        # Example 3
        [
            Paragraph('<b>Example 3: Non-Standard Metric Unit</b><br/><i>(AgroPure Sooji, declared as "500 gms")</i>', table_cell_bold),
            Paragraph(
                '• All 7 presence rules: <b>PASS</b> (14 pts)<br/>'
                '• 3 format rules: <b>PASS</b> (3 pts)<br/>'
                '• LM009 (Unit Symbol): <b>FAIL</b> (0 / 1 pt, "gms" is illegal symbol)<br/>'
                '• Visible defect escalates to violation',
                table_cell_style
            ),
            Paragraph(
                'Passed Weight = 14 + 3 = 17<br/>'
                'Scoreable Weight = 17 + 1 = 18<br/>'
                '<b>Score = 100 × (17 / 18) = 94</b>',
                table_cell_style
            ),
            Paragraph('<b>POTENTIAL_<br/>VIOLATION</b><br/>(Score: 94)', badge_fail)
        ],
        # Example 4
        [
            Paragraph('<b>Example 4: Multiple Statutory Defects</b><br/><i>(QuickBite Noodles)</i>', table_cell_bold),
            Paragraph(
                '• 5 presence rules: <b>PASS</b> (10 pts)<br/>'
                '• LM002 (Address) & LM007 (Care): <b>FAIL</b> (0 / 4 pts)<br/>'
                '• LM009 (Unit): <b>FAIL</b> (0 / 1 pt, "75 gm")<br/>'
                '• 2 format rules: <b>PASS</b> (2 pts)',
                table_cell_style
            ),
            Paragraph(
                'Passed Weight = 10 + 2 = 12<br/>'
                'Scoreable Weight = 12 + 4 + 1 = 17<br/>'
                '<b>Score = 100 × (12 / 17) = 71</b>',
                table_cell_style
            ),
            Paragraph('<b>POTENTIAL_<br/>VIOLATION</b><br/>(Score: 71)', badge_fail)
        ],
    ]
    examples_table = Table(examples_data, colWidths=[40 * mm, 58 * mm, 50 * mm, 32 * mm])
    examples_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
    ]))
    story.append(examples_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # SECTION 7: SUMMARY OF LEGAL & REGULATORY DEFENSIBILITY
    # -------------------------------------------------------------------------
    story.append(Paragraph('7. Legal & Regulatory Defensibility Summary', h1_style))
    defensibility_text = (
        'When presenting this system to government officials, statutory inspectors, or hackathon judges, '
        'the following four core arguments prove the system\'s mathematical and legal soundness:<br/><br/>'
        '• <b>Zero Non-Deterministic Drift:</b> By eliminating AI from the scoring layer, the exact same label will generate '
        'the exact same score (e.g. 88 or 100) regardless of whether it is evaluated today, next month, or in a courtroom demonstration.<br/>'
        '• <b>Direct Gazette Citation:</b> Every finding explicitly references its parent section in the 2011 Gazette '
        '(Rule 6(1)(a) through Rule 9 and Schedules), providing immediate statutory authority for every inspection certificate.<br/>'
        '• <b>Safe Fallback for Incomplete Angles:</b> The engine acknowledges physical photography limits and distinguishes between '
        '<i>"not seen on this photograph"</i> (Needs Review) and <i>"visibly printed defect"</i> (Potential Violation).<br/>'
        '• <b>Extensive Unit Test Validation:</b> The implementation is backed by a 58-assertion deterministic test suite '
        'in <code>backend/test_compliance.py</code> that validates all 15 rules, regex pattern edge cases, and scoring calculations '
        'with a 100% pass rate.'
    )
    story.append(Paragraph(defensibility_text, body_style))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f'PDF successfully generated: {filename}')

if __name__ == '__main__':
    target_path = 'LEGAL_METROLOGY_15_RULES_AND_SCORING_ARCHITECTURE.pdf'
    build_pdf(target_path)
