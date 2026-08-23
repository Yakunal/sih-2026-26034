"""
ai_service.py — the ONLY file that talks to Gemini.

Two functions, and that is the whole AI surface of this project:

    extract_product_data(image_path)  ->  dict   "what does the package say?"
    explain_findings(compliance)      ->  str    plain-language summary of the verdict

WHAT THE AI IS NOT ALLOWED TO DO
--------------------------------
It never decides compliance. It reads the label and reports what it sees; the
deterministic rule engine in compliance.py makes every finding. That boundary
is the core design decision of this project.

The extraction prompt therefore has one job, and the instruction that matters
most is: return null for anything you cannot actually see. A model that fills
in a plausible-looking address it did not read would silently turn a
non-compliant package into a compliant one.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import ComplianceResult, ExtractedData

# Reads backend/.env, then the project root .env.
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
FALLBACK_MODELS = [MODEL, "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
# Remove duplicates while preserving order
FALLBACK_MODELS = list(dict.fromkeys(FALLBACK_MODELS))

API_KEY = os.getenv("GEMINI_API_KEY")

# Filled in by _client() on the first call. See the comment there for why this
# is kept alive rather than built per request.
_CLIENT: genai.Client | None = None


class AINotConfigured(Exception):
    """No GEMINI_API_KEY was found. Live scanning is unavailable; demo mode still works."""


class AIExtractionFailed(Exception):
    """The Gemini call happened but we could not get usable JSON out of it."""


def is_configured() -> bool:
    """True when an API key is present. The UI uses this to decide whether to
    offer live scanning or point the user at demo mode."""
    return bool(API_KEY)


def _client() -> genai.Client:
    if not is_configured():
        raise AINotConfigured(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://aistudio.google.com/apikey — or use Demo Mode, which needs no key."
        )
    # One client for the whole process, built on first use. Reusing it keeps the
    # HTTPS connection open so the second scan is quicker than the first — and,
    # more importantly, a Client closes its own connection pool when it is
    # garbage collected. Writing `genai.Client(...).models.generate_content(...)`
    # creates a client with no lasting reference, which can be collected while
    # the request is still in flight: "Cannot send a request, as the client has
    # been closed." Holding it in a module-level variable avoids that entirely.
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=API_KEY)
    return _CLIENT


# ---------------------------------------------------------------------------
# 1. Image -> structured data
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """
You are reading the label of an Indian pre-packaged commodity for a Legal
Metrology inspection.

Extract ONLY the declarations that are actually visible in this image.

Rules you must follow:
- If you cannot clearly see a declaration, return null for it. Do not guess,
  complete, or infer a value from the brand, the product type, or common sense.
- Copy values as they are printed, including the units and the currency symbol.
  Example: net_quantity "100 g", not "100 grams".
- mrp is just the price ("Rs 50.00"). mrp_text_verbatim is the ENTIRE price line
  exactly as printed ("Maximum Retail Price Rs 50.00 inclusive of all taxes"),
  because the wording itself is what gets checked.
- Do not judge whether the package is legally compliant. That is not your task.
  Only report what is printed.
- Set image_quality to "blurry" if the text is hard to read, "partial" if the
  label is cut off or you can see only one face of the package, otherwise "good".
- Set all_declarations_legible to false if any text is present but unreadable.
- overall_confidence is your confidence in this reading, from 0.0 to 1.0.
"""

# The response schema IS the Pydantic model from models.py. The SDK converts it
# and Gemini is then forced to return exactly those keys, so there is no
# hand-written JSON parsing anywhere in this project.
EXTRACTION_SCHEMA = ExtractedData

_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def extract_product_data(image_path: str | Path) -> dict:
    """
    Send one product image to Gemini and get back a dict of declarations.

    Returns a plain dict with the keys of models.ExtractedData; any declaration
    that is not visible on the label comes back as None.
    """
    image_path = Path(image_path)
    suffix = image_path.suffix.lower()

    if suffix not in _MIME_TYPES:
        raise AIExtractionFailed(f"Unsupported image type '{suffix}'. Use JPG, PNG or WEBP.")

    image_bytes = image_path.read_bytes()
    last_error = None

    for model_name in FALLBACK_MODELS:
        try:
            response = _client().models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=_MIME_TYPES[suffix]),
                    EXTRACTION_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    # temperature 0 -> the same image gives the same reading, which matters
                    # when an inspector re-runs a scan.
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=EXTRACTION_SCHEMA,
                ),
            )

            if not response.text:
                continue

            data = json.loads(response.text)
            return ExtractedData(**data).model_dump()
        except Exception as error:
            last_error = error
            continue

    if last_error:
        raise AIExtractionFailed(f"Gemini extraction failed across models: {last_error}")
    raise AIExtractionFailed("Gemini returned an empty response. The image may have been rejected; try another photo.")


# ---------------------------------------------------------------------------
# 2. Plain-language explanation of a finished verdict
# ---------------------------------------------------------------------------

EXPLANATION_PROMPT = """
You are writing one short paragraph for a Legal Metrology inspection report.

Below are the findings that a deterministic rule engine has ALREADY produced.
Your job is only to restate them in plain language for the inspector.

Do not add legal requirements that are not listed.
Do not change any verdict.
Do not suggest penalties.
Keep it under 80 words.

FINDINGS:
{findings}
"""


def explain_findings(compliance: ComplianceResult) -> str | None:
    """
    Ask Gemini to summarise the rule engine's output in plain English.

    This is cosmetic. If it fails for any reason — no key, no quota, no network —
    we return None and the report simply shows the rule engine's own reasons,
    which are written by hand in compliance.py. A scan never fails because the
    explanation failed.
    """
    if not is_configured():
        return None

    problems = [c for c in compliance.checks if c.result in ("FAIL", "REVIEW")]
    if not problems:
        findings = f"Status: {compliance.status}. Every automatically checkable declaration was found in order."
    else:
        lines = [f"Status: {compliance.status} (score {compliance.score}/100)."]
        for check in problems:
            lines.append(f"- [{check.result}] {check.rule_id} {check.name}: {check.reason}")
        findings = "\n".join(lines)

    try:
        response = _client().models.generate_content(
            model=MODEL,
            contents=EXPLANATION_PROMPT.format(findings=findings),
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=4096),
        )
        return (response.text or "").strip() or None
    except Exception:
        # Deliberately broad: an explanation is never worth failing a scan over.
        return None
