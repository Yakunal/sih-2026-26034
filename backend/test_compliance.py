"""
test_compliance.py — proof that the rule engine is deterministic.

Run it with:      python test_compliance.py
(no pytest, no test framework — just asserts, so anyone can read it)

This is the single most useful file to show a judge who asks
"how do you know the compliance decision is reliable?"
The answer: these fixtures go in, these exact statuses and scores come out,
every time, with no AI involved in the decision.

The four main fixtures are read from sample_data/demo_products.json, so the
demo products shown in the UI and the cases tested here can never drift apart.
"""

import json
import sys
from pathlib import Path

from compliance import (
    MISSING_MANDATORY_FOR_VIOLATION,
    STATUS_COMPLIANT,
    STATUS_NEEDS_REVIEW,
    STATUS_POTENTIAL_VIOLATION,
    check_compliance,
    load_rules,
)

DEMO_FILE = Path(__file__).resolve().parent.parent / "sample_data" / "demo_products.json"

# A label with every declaration correct — used as the base for edge-case tests.
GOOD_LABEL = {
    "product_name": "Test Product",
    "common_generic_name": "Test Commodity",
    "manufacturer_name": "Test Foods Pvt Ltd",
    "manufacturer_address": "1 Test Road, Test City - 100001",
    "net_quantity": "250 g",
    "mrp": "Rs 99",
    "mrp_text_verbatim": "Maximum Retail Price Rs 99 inclusive of all taxes",
    "date_of_packing": "01/2026",
    "consumer_care": "care@test.com",
    "image_quality": "good",
    "all_declarations_legible": True,
}


def _label(**overrides):
    """A copy of GOOD_LABEL with some fields changed."""
    return {**GOOD_LABEL, **overrides}


passed = 0
failed = 0


def check(description, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {description}")
    else:
        failed += 1
        print(f"  FAIL  {description}")
        if detail:
            print(f"        {detail}")


# ---------------------------------------------------------------------------
print("\n[1] rules.json loads and is well formed")
# ---------------------------------------------------------------------------

rules = load_rules()
check(f"{len(rules)} rules loaded", len(rules) == 15, f"expected 15, got {len(rules)}")
check("every rule id is unique", len({r["id"] for r in rules}) == len(rules))
check(
    "every check type is one we implement",
    all(r["check"] in {"presence", "format", "conditional_presence", "manual"} for r in rules),
)
check(
    "every format rule has a pattern",
    all(r["pattern"] for r in rules if r["check"] == "format"),
)
check(
    "manual rules carry no score weight",
    all(r["weight"] == 0 for r in rules if r["check"] == "manual"),
)


# ---------------------------------------------------------------------------
print("\n[2] the four demo products produce their documented verdicts")
# ---------------------------------------------------------------------------

with open(DEMO_FILE, encoding="utf-8") as f:
    demo_products = json.load(f)

for product in demo_products:
    result = check_compliance(product["extracted"])
    check(
        f'{product["id"]} ({product["label"]}) -> {product["expected_status"]}',
        result.status == product["expected_status"],
        f'got {result.status}: {result.status_reason}',
    )
    check(
        f'{product["id"]} score == {product["expected_score"]}',
        result.score == product["expected_score"],
        f'got {result.score}',
    )


# ---------------------------------------------------------------------------
print("\n[3] absence of evidence vs evidence of a defect")
# ---------------------------------------------------------------------------

# One declaration we cannot see -> review, not violation.
one_missing = check_compliance(_label(consumer_care=None))
check(
    "one missing declaration -> NEEDS_REVIEW",
    one_missing.status == STATUS_NEEDS_REVIEW,
    f"got {one_missing.status}",
)

# A declaration we CAN see that is demonstrably wrong -> violation.
bad_unit = check_compliance(_label(net_quantity="250 gms"))
check(
    "non-standard unit symbol '250 gms' -> POTENTIAL_VIOLATION",
    bad_unit.status == STATUS_POTENTIAL_VIOLATION,
    f"got {bad_unit.status}",
)

# Enough missing declarations that "bad photo" stops being the likely story.
many_missing = check_compliance(
    _label(consumer_care=None, mrp=None, mrp_text_verbatim=None, date_of_packing=None)
)
check(
    f"{MISSING_MANDATORY_FOR_VIOLATION}+ missing declarations -> POTENTIAL_VIOLATION",
    many_missing.status == STATUS_POTENTIAL_VIOLATION,
    f"got {many_missing.status}",
)

# A clean label with a good photo.
clean = check_compliance(GOOD_LABEL)
check("a correct label -> COMPLIANT", clean.status == STATUS_COMPLIANT, f"got {clean.status}")
check("a correct label scores 100", clean.score == 100, f"got {clean.score}")


# ---------------------------------------------------------------------------
print("\n[4] a bad photograph never produces a confident finding")
# ---------------------------------------------------------------------------

blurry_but_clean = check_compliance(_label(image_quality="blurry"))
check(
    "blurry image cannot be declared COMPLIANT",
    blurry_but_clean.status == STATUS_NEEDS_REVIEW,
    f"got {blurry_but_clean.status}",
)

blurry_with_defect = check_compliance(_label(image_quality="blurry", net_quantity="250 gms"))
check(
    "blurry image cannot assert a violation either",
    blurry_with_defect.status == STATUS_NEEDS_REVIEW,
    f"got {blurry_with_defect.status}",
)

partial = check_compliance(_label(image_quality="partial"))
check(
    "partial image of an otherwise clean label -> NEEDS_REVIEW",
    partial.status == STATUS_NEEDS_REVIEW,
    f"got {partial.status}",
)


# ---------------------------------------------------------------------------
print("\n[5] conditional rules only fire when they apply")
# ---------------------------------------------------------------------------

domestic = check_compliance(GOOD_LABEL)
country_check = next(c for c in domestic.checks if c.rule_id == "LM012")
check(
    "country of origin is NOT_APPLICABLE with no importer",
    country_check.result == "NOT_APPLICABLE",
    f"got {country_check.result}",
)

imported = check_compliance(_label(importer_name="Global Imports LLP", country_of_origin=None))
country_check = next(c for c in imported.checks if c.rule_id == "LM012")
check(
    "country of origin FAILs once an importer is named",
    country_check.result == "FAIL",
    f"got {country_check.result}",
)
check(
    "an imported package with no country of origin -> POTENTIAL_VIOLATION",
    imported.status == STATUS_POTENTIAL_VIOLATION,
    f"got {imported.status}",
)


# ---------------------------------------------------------------------------
print("\n[6] a missing value is never penalised twice")
# ---------------------------------------------------------------------------

no_mrp = check_compliance(_label(mrp=None, mrp_text_verbatim=None))
presence = next(c for c in no_mrp.checks if c.rule_id == "LM006")
form = next(c for c in no_mrp.checks if c.rule_id == "LM008")
check("missing MRP FAILs the presence rule", presence.result == "FAIL")
check(
    "missing MRP makes the format rule NOT_APPLICABLE (not a second FAIL)",
    form.result == "NOT_APPLICABLE",
    f"got {form.result}",
)


# ---------------------------------------------------------------------------
print("\n[7] the format patterns accept and reject the right strings")
# ---------------------------------------------------------------------------

def format_result(rule_id, **overrides):
    result = check_compliance(_label(**overrides))
    return next(c for c in result.checks if c.rule_id == rule_id).result


# Net quantity — standard symbols in, non-standard abbreviations out.
for value, expected in [
    ("100 g", "PASS"), ("1 kg", "PASS"), ("500 ml", "PASS"), ("1 l", "PASS"),
    ("2.5 kg", "PASS"), ("100g", "PASS"), ("10 N", "PASS"),
    ("100 gms", "FAIL"), ("100 gm", "FAIL"), ("1 ltr", "FAIL"), ("one hundred grams", "FAIL"),
]:
    check(f'net quantity "{value}" -> {expected}', format_result("LM009", net_quantity=value) == expected,
          f'got {format_result("LM009", net_quantity=value)}')

# Date — a month and a year, or nothing.
for value, expected in [
    ("06/2026", "PASS"), ("6/2026", "PASS"), ("JUN 2026", "PASS"), ("Jun. 2026", "PASS"),
    ("06-2026", "PASS"), ("23/08/2026", "PASS"),
    ("2026", "FAIL"), ("13/2026", "FAIL"), ("June", "FAIL"),
]:
    check(f'date "{value}" -> {expected}', format_result("LM010", date_of_packing=value) == expected,
          f'got {format_result("LM010", date_of_packing=value)}')

# MRP — the tax-inclusive wording is what we are looking for.
for value, expected in [
    ("Maximum Retail Price Rs 50 inclusive of all taxes", "PASS"),
    ("MRP Rs. 50/- (incl. of all taxes)", "PASS"),
    ("Rs 50 incl all taxes", "PASS"),
    ("MRP Rs 50", "FAIL"),
    ("Rs 50/-", "FAIL"),
]:
    check(f'MRP line "{value}" -> {expected}',
          format_result("LM008", mrp_text_verbatim=value) == expected,
          f'got {format_result("LM008", mrp_text_verbatim=value)}')

# Consumer care — must offer a real contact route.
for value, expected in [
    ("1800-123-4567", "PASS"),
    ("care@example.com", "PASS"),
    ("Consumer Care Cell, 022 2222 3333", "PASS"),
    ("Consumer Care Department", "FAIL"),
]:
    check(f'consumer care "{value}" -> {expected}',
          format_result("LM011", consumer_care=value) == expected,
          f'got {format_result("LM011", consumer_care=value)}')


# ---------------------------------------------------------------------------
print("\n[8] every check carries an explanation a human can read")
# ---------------------------------------------------------------------------

result = check_compliance(demo_products[3]["extracted"])
check("every check has a reason", all(c.reason for c in result.checks))
check("the overall status has a reason", bool(result.status_reason))
check(
    "manual checks are reported as REVIEW, never guessed",
    all(c.result == "REVIEW" for c in result.checks if c.check_type == "manual"),
)


# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"  {passed} passed, {failed} failed")
print(f"{'=' * 60}\n")
sys.exit(1 if failed else 0)
