"""
models.py — the shapes of data that move through the system.

These are Pydantic models. FastAPI uses them for two things:
  1. validating/serialising JSON responses,
  2. auto-generating the API docs at http://localhost:8000/docs

Reading this file top to bottom tells you the whole data flow:

    ExtractedData     <- what Gemini read off the package image
    RuleCheck         <- the verdict for ONE rule
    ComplianceResult  <- score + overall status + all the RuleChecks
    InspectionDetail  <- everything above, saved with an id and a timestamp
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. What the AI extracted from the image
# ---------------------------------------------------------------------------

class ExtractedData(BaseModel):
    """
    One field per declaration we look for on a package label.

    Every field is optional and defaults to None. `None` means
    "the AI did not see this on the label" — it never means "zero" or
    "empty". The AI is instructed never to guess a value.
    """

    # --- the declarations required by the Rules ---
    product_name: str | None = None            # brand/product as printed, e.g. "Parle-G"
    common_generic_name: str | None = None      # what the thing IS, e.g. "Glucose Biscuits"
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    packer_name: str | None = None              # used when the packer is not the manufacturer
    importer_name: str | None = None            # used for imported packages
    net_quantity: str | None = None             # as printed, e.g. "100 g"
    mrp: str | None = None                      # just the price, e.g. "Rs 50"
    mrp_text_verbatim: str | None = None        # the FULL price line, needed to check wording
    date_of_packing: str | None = None          # as printed, e.g. "06/2026"
    consumer_care: str | None = None            # complaint contact details
    country_of_origin: str | None = None

    # --- the AI's assessment of the photo itself ---
    # This is why we can honestly say "needs review" instead of guessing.
    image_quality: str | None = None            # "good" | "blurry" | "partial"
    all_declarations_legible: bool | None = None
    overall_confidence: float | None = None     # 0.0 - 1.0
    notes: str | None = None                    # anything else worth telling the inspector


# ---------------------------------------------------------------------------
# 2. The result of checking ONE rule
# ---------------------------------------------------------------------------

class RuleCheck(BaseModel):
    """The verdict for a single rule from rules.json."""

    rule_id: str                # "LM001"
    rule_reference: str         # "Rule 6(1)(a)"
    name: str                   # "Manufacturer / packer / importer name"
    requirement: str            # plain-language statement of what the rule wants
    check_type: str             # presence | format | conditional_presence | manual
    weight: int                 # how much this rule contributes to the score

    result: str                 # PASS | FAIL | REVIEW | NOT_APPLICABLE
    observed: str | None = None # the value we actually looked at
    reason: str = ""            # plain-language explanation of the verdict

    escalates: bool = False     # can a FAIL here mean "potential violation"?
    citation_verified: bool = False  # has a human checked this citation against the gazette?


# ---------------------------------------------------------------------------
# 3. The overall compliance verdict
# ---------------------------------------------------------------------------

class ComplianceResult(BaseModel):
    """What the rule engine returns for one product."""

    score: int                  # 0 - 100
    status: str                 # COMPLIANT | NEEDS_REVIEW | POTENTIAL_VIOLATION
    status_reason: str          # WHY we landed on that status — shown in the UI and the PDF

    passed: int
    failed: int
    review: int
    not_applicable: int

    checks: list[RuleCheck]


# ---------------------------------------------------------------------------
# 4. A saved inspection
# ---------------------------------------------------------------------------

class InspectionSummary(BaseModel):
    """One row of the history table / dashboard list."""

    id: int
    product_name: str
    manufacturer: str
    scan_date: str              # ISO-8601 string
    score: int
    status: str
    source: str                 # live_ai | demo_cached | seed


class InspectionDetail(InspectionSummary):
    """Everything about one inspection — used by the result page and the PDF."""

    image_url: str | None = None
    extracted: ExtractedData
    compliance: ComplianceResult
    explanation: str | None = None      # optional plain-language AI summary
    model_used: str | None = None       # which Gemini model produced the extraction


# ---------------------------------------------------------------------------
# 5. Dashboard statistics
# ---------------------------------------------------------------------------

class ViolationCount(BaseModel):
    rule_id: str
    name: str
    count: int


class Stats(BaseModel):
    total: int
    compliant: int
    needs_review: int
    potential_violations: int
    compliance_percentage: int
    average_score: int
    includes_sample_data: bool          # true when seeded rows are part of these numbers
    common_violations: list[ViolationCount]
    recent: list[InspectionSummary]


# ---------------------------------------------------------------------------
# 6. Small response shapes
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    ai_configured: bool
    model: str
    rules_loaded: int
    message: str


class DemoProduct(BaseModel):
    id: str
    label: str                  # "Fully compliant"
    description: str
    expected_status: str
    image_url: str


class ScanResponse(BaseModel):
    """Returned by POST /api/scan and the demo scan endpoint."""

    inspection: InspectionDetail
    is_demo: bool = Field(
        default=False,
        description="True when the EXTRACTION step came from a cached demo file "
                    "instead of a live Gemini call. The rule engine always runs live.",
    )
