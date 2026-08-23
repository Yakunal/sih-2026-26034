"""
check_ai.py — is the API key real, and which models can it actually use?

    python backend/check_ai.py

Run this before a live demo. It answers three questions in order, and stops at
the first one that fails, so you know exactly what is wrong:

    1. Is a key present in .env?
    2. Does Google accept it?               (lists the models it can reach)
    3. Can it read an image with our model? (one real extraction on a demo label)

Nothing here touches the database. It is a read-only probe.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ai_service

DEMO_IMAGE = (
    Path(__file__).resolve().parent.parent / "sample_data" / "demo_images" / "demo-1-compliant.png"
)


def main() -> int:
    print("1. Key present in .env?")
    if not ai_service.is_configured():
        print("   NO. Add GEMINI_API_KEY to .env, then run this again.")
        return 1
    key = ai_service.API_KEY
    print(f"   Yes — {key[:6]}...{key[-4:]} ({len(key)} characters)")
    print(f"   Model requested in .env: {ai_service.MODEL}")

    print("\n2. Does Google accept the key?")
    try:
        client = ai_service._client()
        names = []
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if not actions or "generateContent" in actions:
                names.append((model.name or "").replace("models/", ""))
    except Exception as error:
        print(f"   NO. {type(error).__name__}: {error}")
        return 1

    print(f"   Yes — {len(names)} models available for generateContent.")
    flash = [n for n in names if "flash" in n and "thinking" not in n]
    for name in flash[:25]:
        marker = "  <-- our default" if name == ai_service.MODEL else ""
        print(f"     {name}{marker}")
    if ai_service.MODEL not in names:
        print(f"\n   WARNING: '{ai_service.MODEL}' is NOT in the list above.")
        print("   Set GEMINI_MODEL in .env to one of those names.")

    print("\n3. Can it read a label image?")
    if not DEMO_IMAGE.exists():
        print(f"   Skipped — {DEMO_IMAGE} not found. Run sample_data/generate_demo_images.py")
        return 1
    try:
        data = ai_service.extract_product_data(DEMO_IMAGE)
    except Exception as error:
        print(f"   NO. {type(error).__name__}: {error}")
        return 1

    found = {k: v for k, v in data.items() if v not in (None, "")}
    print(f"   Yes — {len(found)} of {len(data)} fields came back filled.")
    for field in ("product_name", "net_quantity", "mrp", "mrp_text_verbatim", "image_quality"):
        print(f"     {field}: {data.get(field)!r}")

    print("\nLIVE AI IS WORKING.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
