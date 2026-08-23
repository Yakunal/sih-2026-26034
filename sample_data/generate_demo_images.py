"""
generate_demo_images.py — draws the four demo package labels.

Run it once before the demo:

    python sample_data/generate_demo_images.py

WHY GENERATE THEM?
------------------
Two reasons, and both matter for an honest demo:

1. The demo works with no internet and no API key.
2. The image genuinely CONTAINS the defect its cached result describes. Demo
   product 4 really does say "100 gms" and really does print the price with no
   tax-inclusive wording. So when a key is available, sending the same image to
   Gemini reproduces the cached reading — the cached result is a recording of a
   real extraction, not a fabrication.

Replacing these with real photographs later: drop your photos into
sample_data/demo_images/ using the same filenames listed in demo_products.json
(or pass --images-dir to write elsewhere). Nothing else needs to change.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DEMO_PRODUCTS_FILE = HERE / "demo_products.json"
DEFAULT_OUTPUT_DIR = HERE / "demo_images"

WIDTH = 900  # the height is computed from the content of each label

# Flat-design palette, matching the web UI.
WHITE = "#FFFFFF"
INK = "#111827"
GRAY = "#6B7280"
MUTED = "#F3F4F6"

# Candidate fonts, tried in order. Different machines have different fonts
# installed, so we look for several and fall back to Pillow's built-in.
BOLD_FONTS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/seguisb.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
REGULAR_FONTS = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for candidate in BOLD_FONTS if bold else REGULAR_FONTS:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------------------
# What is printed on each label.
#
# These strings are the source of truth for the images. The cached extractions
# in demo_products.json describe exactly what a reader would see here —
# including the deliberate defects.
# ---------------------------------------------------------------------------

LABELS = {
    "demo-1": {
        "theme": "#3B82F6",
        "brand": "KRISP GOLD",
        "generic": "Glucose Biscuits",
        "declarations": [
            ("Manufactured & Marketed by", "Krisp Foods Private Limited"),
            ("", "Plot 14, Phase II, Okhla Industrial Area,"),
            ("", "New Delhi - 110020"),
            ("Net Quantity", "100 g"),
            ("Maximum Retail Price", "Rs 50.00 (inclusive of all taxes)"),
            ("Packed in (month/year)", "06/2026"),
        ],
        "footer": "Consumer care: care@krispfoods.in / 1800-123-4567",
    },
    "demo-2": {
        "theme": "#10B981",
        "brand": "NUTRI MORNING",
        "generic": "Wheat Flakes",
        "declarations": [
            ("Manufactured by", "Sunrise Cereals Pvt Ltd"),
            ("", "Survey No. 88, Bhosari MIDC,"),
            ("", "Pune - 411026"),
            ("Net Quantity", "375 g"),
            ("Packed in (month/year)", "05/2026"),
            # No price declaration anywhere on this label - that is the defect.
        ],
        "footer": "Customer care: 1800-222-9090, help@sunrisecereals.com",
    },
    "demo-3": {
        "theme": "#F59E0B",
        "brand": "FARM PURE",
        "generic": "Refined Sunflower Oil",
        "declarations": [
            ("Manufactured by", "Farm Pure Oils Limited"),
            ("", "44/A, GIDC Estate, Rajkot - 360003,"),
            ("", "Gujarat"),
            ("Net Quantity", "1 l"),
            ("MRP", "Rs 165.00 incl. of all taxes"),
            ("Packed in (month/year)", "07/2026"),
        ],
        # No consumer care line at all - that is the defect.
        "footer": None,
    },
    "demo-4": {
        "theme": "#111827",
        "brand": "SPICE ROUTE",
        "generic": "Turmeric Powder",
        "declarations": [
            ("Packed by", "Spice Route Traders"),
            ("", "Shop 7, Market Yard, Sangli - 416416"),
            ("Net Quantity", "100 gms"),          # defect: non-standard unit symbol
            ("MRP", "Rs 40/-"),                   # defect: no tax-inclusive wording
            ("Packed in", "2026"),                # defect: no month
        ],
        # Also no consumer care line.
        "footer": None,
    },
}


def wrap(draw, text, text_font, max_width):
    """Break text into lines that fit inside max_width pixels."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=text_font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


MARGIN = 60
HEADER_HEIGHT = 300
INNER_WIDTH = WIDTH - 2 * MARGIN


def draw_label(spec: dict) -> Image.Image:
    """
    Draw one flat-design package label.

    Done in two passes: measure the text first so the canvas can be sized to its
    content, then draw. Otherwise a product with fewer declarations (demo 4 has
    no consumer care line) ends up with a large empty area at the bottom.
    """
    label_font = font(20, bold=True)
    value_font = font(30)
    footer_font = font(24)

    # --- Pass 1: measure -------------------------------------------------
    ruler = ImageDraw.Draw(Image.new("RGB", (WIDTH, 10)))

    body: list[tuple[str, list[str]]] = []
    body_height = 0
    for label_text, value_text in spec["declarations"]:
        lines = wrap(ruler, value_text, value_font, INNER_WIDTH)
        body.append((label_text, lines))
        body_height += (30 if label_text else 0) + 40 * len(lines) + 18

    footer_lines = wrap(ruler, spec["footer"], footer_font, INNER_WIDTH) if spec["footer"] else []
    footer_height = 34 * len(footer_lines) + 80 if footer_lines else 0

    height = HEADER_HEIGHT + 70 + body_height + 40 + footer_height

    # --- Pass 2: draw ----------------------------------------------------
    image = Image.new("RGB", (WIDTH, height), WHITE)
    draw = ImageDraw.Draw(image)

    # Header: a solid colour block. No gradient, no shadow.
    draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=spec["theme"])

    # Decorative flat circle outline, bleeding off the top-right corner.
    draw.ellipse([WIDTH - 175, -75, WIDTH + 75, 175], outline=WHITE, width=6)

    draw.text((MARGIN, 90), spec["brand"], font=font(64, bold=True), fill=WHITE)
    draw.text((MARGIN, 175), spec["generic"], font=font(34), fill=WHITE)
    draw.text((MARGIN, 235), "PRE-PACKAGED COMMODITY", font=font(20, bold=True), fill=WHITE)

    y = HEADER_HEIGHT + 70
    for label_text, lines in body:
        if label_text:
            draw.text((MARGIN, y), label_text.upper(), font=label_font, fill=GRAY)
            y += 30
        for line in lines:
            draw.text((MARGIN, y), line, font=value_font, fill=INK)
            y += 40
        y += 18

    if footer_lines:
        band_top = height - footer_height
        draw.rectangle([0, band_top, WIDTH, height], fill=MUTED)
        text_y = band_top + 40
        for line in footer_lines:
            draw.text((MARGIN, text_y), line, font=footer_font, fill=INK)
            text_y += 34

    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the four demo package label images.")
    parser.add_argument(
        "--images-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Where to write the images (default: sample_data/demo_images).",
    )
    args = parser.parse_args()

    output_dir = Path(args.images_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(DEMO_PRODUCTS_FILE, encoding="utf-8") as f:
        products = json.load(f)

    print(f"Writing demo label images to {output_dir}\n")

    for product in products:
        spec = LABELS.get(product["id"])
        if spec is None:
            print(f"  skipped {product['id']} - no label design defined")
            continue

        destination = output_dir / product["image_file"]
        draw_label(spec).save(destination, "PNG")
        print(f"  {product['image_file']:<38} {product['label']} -> expects {product['expected_status']}")

    print(f"\nDone. {len(products)} images ready for Demo Mode.")


if __name__ == "__main__":
    main()
