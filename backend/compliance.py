"""
compliance.py — THE RULE ENGINE.

This is the file to read if you want to understand how the system decides
compliance. It is deliberately plain Python: no AI, no machine learning, no
randomness. Same input -> same output, every time.

    Gemini's job:      "what does the package say?"     (ai_service.py)
    This file's job:   "does that satisfy the rule?"

Why the split matters: a legal finding has to be traceable and repeatable.
If a judge asks "why did this package fail?", the answer is a rule id, the
value we looked at, and a line of code — not "the model thought so".

--------------------------------------------------------------------------
HOW A RULE IS CHECKED
--------------------------------------------------------------------------
Every rule in rules.json has a "check" type, and each type has one small
function below:

  presence             -> is the declaration there at all?
  format               -> the declaration is there; is it in the prescribed form?
  conditional_presence -> required only in certain cases (e.g. imported goods)
  manual               -> cannot be decided from a photograph; always REVIEW

--------------------------------------------------------------------------
HOW THE OVERALL STATUS IS DECIDED  (the important design decision)
--------------------------------------------------------------------------
We distinguish two very different kinds of failure:

  Absence of evidence  -> NEEDS_REVIEW
      A required declaration is not visible. But one photograph shows one or
      two faces of a package: the declaration may well be printed on a panel
      the camera never saw. We are not entitled to call that a violation.

  Evidence of a defect -> POTENTIAL_VIOLATION
      The declaration IS visible and is demonstrably wrong: a price with no
      "inclusive of all taxes" wording, "100 gms" instead of "100 g", a date
      that names no month. Here we can point at the defect in the image.

That distinction is what makes the output defensible, and it is why rules.json
carries an "escalates" flag per rule.
"""

import json
import re
from pathlib import Path

from models import ComplianceResult, RuleCheck

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

RULES_PATH = Path(__file__).parent / "rules.json"

# The three possible verdicts for a whole product.
STATUS_COMPLIANT = "COMPLIANT"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"
STATUS_POTENTIAL_VIOLATION = "POTENTIAL_VIOLATION"

# The four possible verdicts for a single rule.
PASS = "PASS"
FAIL = "FAIL"
REVIEW = "REVIEW"
NOT_APPLICABLE = "NOT_APPLICABLE"

# If this many mandatory declarations are missing at once, the label is far more
# likely to be genuinely non-compliant than merely photographed badly, so we
# stop giving it the benefit of the doubt.
MISSING_MANDATORY_FOR_VIOLATION = 3

# Values that look like data but actually mean "nothing was found".
_EMPTY_VALUES = {"", "-", "—", "n/a", "na", "none", "null", "not visible", "not found"}


# --------------------------------------------------------------------------
# Loading the rules
# --------------------------------------------------------------------------

def load_rules() -> list[dict]:
    """Read rules.json from disk. Called on every request so you can edit the
    rules and refresh the page without restarting the server."""
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _is_empty(value) -> bool:
    """True when the AI gave us nothing usable for this field."""
    if value is None:
        return True
    text = str(value).strip()
    return text.lower() in _EMPTY_VALUES


def _first_available(data: dict, field: str | None, alt_fields: list[str]) -> tuple[str | None, str | None]:
    """
    Return (value, field_name_it_came_from) for the first field that has a value.

    Rules use alt_fields when the law accepts alternatives — for example the
    name may be that of the manufacturer OR the packer OR the importer.
    """
    for name in [field] + (alt_fields or []):
        if not name:
            continue
        value = data.get(name)
        if not _is_empty(value):
            return str(value).strip(), name
    return None, None


def _pretty(field_name: str | None) -> str:
    """'manufacturer_name' -> 'manufacturer name' (for readable messages)."""
    return (field_name or "").replace("_", " ")


# --------------------------------------------------------------------------
# The four check types — one function each
# --------------------------------------------------------------------------

def _check_presence(rule: dict, data: dict) -> tuple[str, str | None, str]:
    """Is the declaration present at all?"""
    value, source_field = _first_available(data, rule["field"], rule.get("alt_fields", []))

    if value is None:
        looked_at = ", ".join(_pretty(f) for f in [rule["field"]] + rule.get("alt_fields", []) if f)
        return FAIL, None, f"No value was detected for: {looked_at}."

    note = f"Detected as '{value}'"
    if source_field != rule["field"]:
        note += f" (accepted via the alternative declaration '{_pretty(source_field)}')"
    return PASS, value, note + "."


def _check_format(rule: dict, data: dict) -> tuple[str, str | None, str]:
    """
    The declaration exists — is it in the prescribed form?

    Note: if the value is MISSING we return NOT_APPLICABLE rather than FAIL.
    The matching presence rule already reports the absence; failing it twice
    would punish the same defect two times and distort the score.
    """
    value, _ = _first_available(data, rule["field"], rule.get("alt_fields", []))

    if value is None:
        return NOT_APPLICABLE, None, (
            f"Not checked: no {_pretty(rule['field'])} was detected, so there is "
            f"nothing to check the format of."
        )

    if re.search(rule["pattern"], value):
        return PASS, value, f"'{value}' matches the prescribed form."

    return FAIL, value, f"'{value}' was found on the label but does not match the prescribed form."


def _check_conditional_presence(rule: dict, data: dict) -> tuple[str, str | None, str]:
    """Required only when a trigger field tells us the rule applies."""
    trigger_value, _ = _first_available(data, rule["trigger_field"], [])

    if trigger_value is None:
        return NOT_APPLICABLE, None, (
            f"Not applicable: no {_pretty(rule['trigger_field'])} was detected, "
            f"so this appears not to be an imported package."
        )

    value, _ = _first_available(data, rule["field"], rule.get("alt_fields", []))
    if value is None:
        return FAIL, None, (
            f"An importer ('{trigger_value}') was detected, which makes this rule apply, "
            f"but no {_pretty(rule['field'])} was found."
        )
    return PASS, value, f"Detected as '{value}'."


def _check_manual(rule: dict, data: dict) -> tuple[str, str | None, str]:
    """
    Cannot honestly be decided from an uploaded photograph.

    We say so plainly instead of inventing a measurement. Font height, for
    instance, is a millimetre measurement against the area of the display
    panel — not something to guess from an arbitrary phone photo.
    """
    return REVIEW, None, "Requires physical verification of the package; not determinable from an image."


# Maps the "check" value in rules.json to the function that handles it.
CHECK_FUNCTIONS = {
    "presence": _check_presence,
    "format": _check_format,
    "conditional_presence": _check_conditional_presence,
    "manual": _check_manual,
}


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _calculate_score(checks: list[RuleCheck]) -> int:
    """
    score = 100 * (weight of rules that passed) / (weight of rules we could score)

    Only PASS and FAIL count. REVIEW and NOT_APPLICABLE are excluded from both
    halves of the fraction, so a package is never penalised for a rule we
    honestly could not evaluate.
    """
    scoreable = [c for c in checks if c.result in (PASS, FAIL)]
    total_weight = sum(c.weight for c in scoreable)

    if total_weight == 0:
        return 0

    earned_weight = sum(c.weight for c in scoreable if c.result == PASS)
    return round(100 * earned_weight / total_weight)


# --------------------------------------------------------------------------
# Deciding the overall status
# --------------------------------------------------------------------------

def _decide_status(checks: list[RuleCheck], data: dict) -> tuple[str, str]:
    """Returns (status, human-readable reason). See the module docstring."""

    # A visible defect we can point at.
    defects = [c for c in checks if c.result == FAIL and c.escalates]
    # A declaration we simply could not see.
    missing = [c for c in checks if c.result == FAIL and not c.escalates]
    reviews = [c for c in checks if c.result == REVIEW]

    # A blurry photo undermines every finding, in both directions: we can
    # neither confirm compliance nor assert a defect. Say so and stop.
    if (data.get("image_quality") or "").lower() == "blurry":
        return STATUS_NEEDS_REVIEW, (
            "The image was reported as blurry, so no finding can be asserted from it. "
            "Re-photograph the package in better light, or inspect it physically."
        )

    if defects:
        ids = ", ".join(c.rule_id for c in defects)
        return STATUS_POTENTIAL_VIOLATION, (
            f"{len(defects)} declaration(s) are visible on the label but are not in the "
            f"prescribed form ({ids}). Because the defect is visible in the image, this is "
            f"reported as a potential violation rather than a review item."
        )

    if len(missing) >= MISSING_MANDATORY_FOR_VIOLATION:
        ids = ", ".join(c.rule_id for c in missing)
        return STATUS_POTENTIAL_VIOLATION, (
            f"{len(missing)} mandatory declarations were not detected ({ids}). With this many "
            f"absent at once, an incomplete label is a more likely explanation than a "
            f"partial photograph."
        )

    if missing:
        ids = ", ".join(c.rule_id for c in missing)
        return STATUS_NEEDS_REVIEW, (
            f"{len(missing)} mandatory declaration(s) were not detected ({ids}). A single "
            f"photograph may not show every panel of the package, so this is flagged for "
            f"manual review rather than reported as a violation."
        )

    if (data.get("image_quality") or "").lower() == "partial" or data.get("all_declarations_legible") is False:
        return STATUS_NEEDS_REVIEW, (
            "Every implemented check passed, but the image shows only part of the label or "
            "some text was not fully legible. A physical check is recommended before clearing it."
        )

    return STATUS_COMPLIANT, (
        f"All {len([c for c in checks if c.result == PASS])} automatically checkable declarations "
        f"were found in the prescribed form. {len(reviews)} item(s) still need physical "
        f"verification and are listed below."
    )


# --------------------------------------------------------------------------
# The main entry point
# --------------------------------------------------------------------------

def check_compliance(extracted: dict) -> ComplianceResult:
    """
    Run every rule in rules.json against one extraction and return the verdict.

    `extracted` is the plain dict that came out of ai_service.extract_product_data()
    (or out of a cached demo file — the rule engine cannot tell the difference,
    which is exactly why demo mode is honest).
    """
    checks: list[RuleCheck] = []

    for rule in load_rules():
        check_function = CHECK_FUNCTIONS[rule["check"]]
        result, observed, reason = check_function(rule, extracted)

        checks.append(
            RuleCheck(
                rule_id=rule["id"],
                rule_reference=rule["rule_reference"],
                name=rule["name"],
                requirement=rule["requirement"],
                check_type=rule["check"],
                weight=rule["weight"],
                result=result,
                observed=observed,
                reason=reason,
                escalates=rule["escalates"],
                citation_verified=rule["citation_verified"],
            )
        )

    status, status_reason = _decide_status(checks, extracted)

    return ComplianceResult(
        score=_calculate_score(checks),
        status=status,
        status_reason=status_reason,
        passed=len([c for c in checks if c.result == PASS]),
        failed=len([c for c in checks if c.result == FAIL]),
        review=len([c for c in checks if c.result == REVIEW]),
        not_applicable=len([c for c in checks if c.result == NOT_APPLICABLE]),
        checks=checks,
    )
