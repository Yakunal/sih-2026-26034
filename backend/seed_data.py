"""
seed_data.py — fills the database with sample past inspections.

Run it once so the dashboard and history page have something to show:

    python backend/seed_data.py            # add ~20 sample inspections
    python backend/seed_data.py --reset     # delete everything first

HONESTY NOTE
------------
These rows are invented for demonstration. They are written with
source = 'seed', every screen that counts them shows an "includes sample data"
note, and their PDF reports are stamped "SAMPLE DATA - generated for
demonstration, not a real inspection". Nothing here is presented as a real scan.

The rows are still internally consistent: each one is built as a label reading
and then run through the SAME rule engine the live path uses. So the score,
status and per-rule results are genuinely computed, not typed in by hand. That
also means the dashboard's "most common violations" tally is real.
"""

import argparse
from datetime import datetime, timedelta

import database
from compliance import check_compliance

# A correctly labelled package. Every sample below starts from this and breaks
# specific things, which is much easier to read than 20 full dictionaries.
COMPLIANT_BASE = {
    "product_name": None,
    "common_generic_name": None,
    "manufacturer_name": None,
    "manufacturer_address": "Plot 21, Industrial Estate, Pune - 411019, Maharashtra",
    "packer_name": None,
    "importer_name": None,
    "net_quantity": "500 g",
    "mrp": "Rs 120.00",
    "mrp_text_verbatim": "Maximum Retail Price Rs 120.00 (inclusive of all taxes)",
    "date_of_packing": "05/2026",
    "consumer_care": "care@example.in / 1800-100-2000",
    "country_of_origin": None,
    "image_quality": "good",
    "all_declarations_legible": True,
    "overall_confidence": 0.9,
    "notes": None,
}

# (product, generic name, manufacturer, what is wrong with this label)
SAMPLES = [
    ("Anand Toor Dal", "Toor Dal (Split Pigeon Pea)", "Anand Agro Foods Pvt Ltd", {}),
    ("Sunfeast Marie", "Marie Biscuits", "Bharat Bakers Limited", {}),
    ("Everyday Tea Gold", "Black Tea", "Nilgiri Tea Estates Ltd", {}),
    ("Shakti Atta", "Whole Wheat Flour", "Shakti Mills Private Limited", {}),
    ("Cool Sip Mango", "Mango Fruit Drink", "Cool Sip Beverages Ltd", {}),
    ("Nature Fresh Honey", "Honey", "Nature Fresh Apiaries", {}),

    # Missing a mandatory declaration -> NEEDS_REVIEW (it may be on another panel)
    ("Gopal Mustard Oil", "Mustard Oil", "Gopal Oil Mills", {"mrp": None, "mrp_text_verbatim": None}),
    ("Amrit Besan", "Bengal Gram Flour", "Amrit Flour Mills", {"consumer_care": None}),
    ("Sagar Salt", "Iodised Salt", "Sagar Salt Works Ltd", {"date_of_packing": None}),
    ("Krishna Poha", "Flattened Rice", "Krishna Foods", {"manufacturer_address": None}),
    ("Deepam Coconut Oil", "Coconut Oil", "Deepam Products", {"net_quantity": None}),
    ("Milan Rusk", "Wheat Rusk", "Milan Bakery Products", {"consumer_care": None}),

    # Visible defects -> POTENTIAL_VIOLATION
    ("Ratna Chilli Powder", "Red Chilli Powder", "Ratna Spices", {
        "net_quantity": "200 gms",
        "mrp_text_verbatim": "MRP Rs 85/-",
    }),
    ("Gold Star Ghee", "Cow Ghee", "Gold Star Dairy", {
        "mrp_text_verbatim": "Rs 540",
        "date_of_packing": "2026",
    }),
    ("Vimal Papad", "Papad", "Vimal Home Foods", {
        "net_quantity": "100 gm",
        "consumer_care": "Customer Care Department",
    }),
    ("Sri Balaji Jaggery", "Jaggery", "Sri Balaji Sugars", {
        "mrp_text_verbatim": "Price Rs 60",
        "net_quantity": "1 kilo",
        "consumer_care": None,
    }),

    # Imported packages: country of origin becomes applicable
    ("Olivia Olive Oil", "Extra Virgin Olive Oil", None, {
        "importer_name": "Olivia Imports India Pvt Ltd",
        "country_of_origin": "Spain",
        "net_quantity": "750 ml",
    }),
    ("Alpine Dark Chocolate", "Dark Chocolate", None, {
        "importer_name": "Alpine Confections India Pvt Ltd",
        "country_of_origin": None,          # imported but no origin declared -> defect
        "net_quantity": "100 g",
    }),

    # Poor photographs -> NEEDS_REVIEW regardless of what was read
    ("Suraj Sooji", "Semolina", "Suraj Mills", {
        "image_quality": "blurry",
        "all_declarations_legible": False,
        "overall_confidence": 0.42,
        "mrp": None,
        "mrp_text_verbatim": None,
    }),
    ("Anmol Cashew", "Cashew Kernels", "Anmol Dry Fruits", {
        "image_quality": "partial",
        "overall_confidence": 0.55,
        "consumer_care": None,
    }),
]


def build_reading(product_name, generic_name, manufacturer, overrides) -> dict:
    """One sample label reading: the compliant base with specific things broken."""
    reading = dict(COMPLIANT_BASE)
    reading["product_name"] = product_name
    reading["common_generic_name"] = generic_name
    reading["manufacturer_name"] = manufacturer
    reading.update(overrides)
    return reading


def seed(reset: bool = False) -> None:
    database.init_db()

    if reset:
        with database.get_connection() as connection:
            deleted = connection.execute("DELETE FROM inspections").rowcount
        print(f"Deleted {deleted} existing inspection(s).\n")

    # Spread the sample inspections back over the past few weeks so the history
    # page does not show twenty rows with the same timestamp.
    now = datetime.now()
    tally: dict[str, int] = {}

    for index, (product, generic, manufacturer, overrides) in enumerate(SAMPLES):
        reading = build_reading(product, generic, manufacturer, overrides)

        # The real rule engine, not hand-written results.
        result = check_compliance(reading)
        tally[result.status] = tally.get(result.status, 0) + 1

        scan_date = now - timedelta(days=index, hours=index * 3 % 24)

        database.save_inspection(
            extracted=reading,
            compliance=result,
            image_filename=None,          # sample rows have no photograph
            scan_date=scan_date.isoformat(timespec="seconds"),
            source=database.SOURCE_SEED,
            model_used=None,
            explanation=None,
        )
        print(f"  {result.status:<20} {result.score:>3}  {product}")

    print(f"\nAdded {len(SAMPLES)} sample inspections.")
    for status, count in sorted(tally.items()):
        print(f"  {status}: {count}")
    print("\nAll marked source='seed' - the dashboard shows an 'includes sample data' note.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert sample inspections for the demo dashboard.")
    parser.add_argument("--reset", action="store_true", help="Delete all existing inspections first.")
    seed(reset=parser.parse_args().reset)
