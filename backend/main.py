"""
main.py — the whole API.

One file, one FastAPI app, about ten endpoints. Start it with:

    python -m uvicorn main:app --reload --port 8000

Interactive API docs are then at http://localhost:8000/docs

THE FLOW, IN ONE PLACE
----------------------
POST /api/scan is the endpoint that matters. Read it top to bottom and you have
read the entire product:

    1. save the uploaded image to uploads/
    2. ai_service.extract_product_data()   -> what the label says      (AI)
    3. compliance.check_compliance()       -> does it satisfy the rules (NOT AI)
    4. ai_service.explain_findings()       -> plain-language summary    (AI, optional)
    5. database.save_inspection()          -> SQLite
    6. return the result; the PDF is generated later, on request
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import ai_service
import database
from compliance import check_compliance, load_rules
from models import (
    DemoProduct,
    HealthResponse,
    InspectionDetail,
    InspectionSummary,
    ScanResponse,
    Stats,
)
from report import generate_report

import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("/tmp") if os.getenv("VERCEL") else BASE_DIR
UPLOADS_DIR = DATA_DIR / "uploads"
DEMO_DIR = BASE_DIR.parent / "sample_data"
DEMO_PRODUCTS_FILE = DEMO_DIR / "demo_products.json"
DEMO_IMAGES_DIR = DEMO_DIR / "demo_images"

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

app = FastAPI(
    title="Legal Metrology Compliance Checker",
    description=(
        "Prototype for SIH26034. Extracts declarations from a packaged-commodity image with "
        "Gemini, then checks them against implemented rules from the Legal Metrology "
        "(Packaged Commodities) Rules, 2011 using a deterministic rule engine."
    ),
    version="1.0.0",
)

# Allow CORS for local dev and cloud deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

# Create the SQLite file and table if this is the first run. Runs once, on import.
database.init_db()


# ---------------------------------------------------------------------------
# Health & Root
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    """If the frontend was built, serve index.html; otherwise redirect to /docs."""
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return RedirectResponse(url="/docs")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Tells the frontend whether live scanning is available.

    With no GEMINI_API_KEY the app still works completely through Demo Mode, so
    the UI needs to know which of the two to offer.
    """
    configured = ai_service.is_configured()
    return HealthResponse(
        ai_configured=configured,
        model=ai_service.MODEL,
        rules_loaded=len(load_rules()),
        message=(
            "Live AI scanning is available."
            if configured
            else "No GEMINI_API_KEY found. Demo Mode works without a key; add a key to .env for live scanning."
        ),
    )


# ---------------------------------------------------------------------------
# Scanning a real upload
# ---------------------------------------------------------------------------

def _store_upload(upload: UploadFile) -> str:
    """Validate the uploaded file and save it into uploads/. Returns the filename."""
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix or 'unknown'}'. Please upload a JPG, PNG or WEBP image.",
        )

    contents = upload.file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image is larger than 10 MB. Please upload a smaller photo.")
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    filename = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{suffix}"
    (UPLOADS_DIR / filename).write_bytes(contents)
    return filename


@app.post("/api/scan", response_model=ScanResponse)
def scan_product(image: UploadFile = File(...)) -> ScanResponse:
    """
    The main endpoint: an image goes in, a full compliance result comes out.

    The five steps below are the entire product. Note which ones use the AI and
    which do not — step 3 is the only one that decides anything.
    """
    filename = _store_upload(image)
    image_path = UPLOADS_DIR / filename

    # Step 1: the AI reads the label. This is the only step that needs a key.
    try:
        extracted = ai_service.extract_product_data(image_path)
    except ai_service.AINotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ai_service.AIExtractionFailed as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        # Network problems, quota exhaustion, a model refusal — all land here.
        raise HTTPException(
            status_code=502,
            detail=f"The AI extraction step failed: {error}. You can still use Demo Mode.",
        ) from error

    # Step 2 & 3: the rule engine decides. No AI involved.
    result = check_compliance(extracted)

    # Step 4: optional plain-language summary. Never fatal.
    explanation = ai_service.explain_findings(result)

    # Step 5: save, so the inspection appears in history and can be reported on.
    inspection_id = database.save_inspection(
        extracted=extracted,
        compliance=result,
        image_filename=filename,
        scan_date=datetime.now().isoformat(timespec="seconds"),
        source=database.SOURCE_LIVE_AI,
        model_used=ai_service.MODEL,
        explanation=explanation,
    )

    return ScanResponse(inspection=database.get_inspection(inspection_id), is_demo=False)


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------

def _load_demo_products() -> list[dict]:
    if not DEMO_PRODUCTS_FILE.exists():
        raise HTTPException(status_code=500, detail="sample_data/demo_products.json is missing.")
    with open(DEMO_PRODUCTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _copy_demo_image(image_file: str) -> str | None:
    """
    Copy a demo image into uploads/ so it is served from the same place as real
    uploads. Returns the filename, or None if the image has not been generated yet.
    """
    source = DEMO_IMAGES_DIR / image_file
    if not source.exists():
        return None
    destination = UPLOADS_DIR / image_file
    if not destination.exists():
        shutil.copyfile(source, destination)
    return image_file


@app.get("/api/demo-products", response_model=list[DemoProduct])
def demo_products() -> list[DemoProduct]:
    """The prepared products used for the demo. These need no API key."""
    products = []
    for product in _load_demo_products():
        filename = _copy_demo_image(product["image_file"])
        products.append(
            DemoProduct(
                id=product["id"],
                label=product["label"],
                description=product["description"],
                expected_status=product["expected_status"],
                image_url=f"/uploads/{filename}" if filename else "",
            )
        )
    return products


@app.post("/api/demo-products/{demo_id}/scan", response_model=ScanResponse)
def scan_demo_product(
    demo_id: str,
    live: bool = Query(
        default=False,
        description="False (default) uses the cached extraction. True sends the demo image to "
                    "Gemini for a genuine live reading — requires an API key.",
    ),
) -> ScanResponse:
    """
    Run a prepared demo product through the pipeline.

    IMPORTANT, and worth saying out loud to judges: only the EXTRACTION step is
    cached. The rule engine, the scoring, the database write and the PDF all run
    live, exactly as they do for a real upload. The result is labelled as a demo
    everywhere it appears — we never present a cached reading as fresh AI output.
    """
    product = next((p for p in _load_demo_products() if p["id"] == demo_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail=f"No demo product with id '{demo_id}'.")

    filename = _copy_demo_image(product["image_file"])

    if live:
        if not ai_service.is_configured():
            raise HTTPException(
                status_code=503,
                detail="A live run needs GEMINI_API_KEY in .env. Without it, use the cached demo result.",
            )
        if filename is None:
            raise HTTPException(
                status_code=400,
                detail="The demo image has not been generated yet. Run: python sample_data/generate_demo_images.py",
            )
        try:
            extracted = ai_service.extract_product_data(UPLOADS_DIR / filename)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Live extraction failed: {error}") from error
        source, model_used = database.SOURCE_LIVE_AI, ai_service.MODEL
    else:
        # The cached reading of this same image.
        extracted = product["extracted"]
        source, model_used = database.SOURCE_DEMO_CACHED, None

    compliance_result = check_compliance(extracted)
    explanation = ai_service.explain_findings(compliance_result)

    inspection_id = database.save_inspection(
        extracted=extracted,
        compliance=compliance_result,
        image_filename=filename,
        scan_date=datetime.now().isoformat(timespec="seconds"),
        source=source,
        model_used=model_used,
        explanation=explanation,
    )

    return ScanResponse(inspection=database.get_inspection(inspection_id), is_demo=not live)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@app.get("/api/inspections", response_model=list[InspectionSummary])
def list_inspections(
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None, description="Filter by COMPLIANT / NEEDS_REVIEW / POTENTIAL_VIOLATION"),
) -> list[InspectionSummary]:
    return database.list_inspections(limit=limit, status=status)


@app.get("/api/inspections/{inspection_id}", response_model=InspectionDetail)
def get_inspection(inspection_id: int) -> InspectionDetail:
    inspection = database.get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail=f"No inspection with id {inspection_id}.")
    return inspection


@app.get("/api/inspections/{inspection_id}/report")
def download_report(inspection_id: int) -> FileResponse:
    """Generate the PDF on demand and send it back as a download."""
    inspection = database.get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail=f"No inspection with id {inspection_id}.")

    pdf_path = generate_report(inspection)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"compliance_report_{inspection_id}.pdf",
    )


# ---------------------------------------------------------------------------
# Dashboard and rules
# ---------------------------------------------------------------------------

@app.get("/api/stats", response_model=Stats)
def stats() -> Stats:
    return database.get_stats()


@app.get("/api/rules")
def rules() -> dict:
    """
    The implemented rules, exactly as the engine reads them.

    Exposed so the UI can show judges what is and is not implemented — including
    which citations still need cross-checking against the official gazette text.
    """
    all_rules = load_rules()
    return {
        "total": len(all_rules),
        "scoreable": len([r for r in all_rules if r["check"] != "manual"]),
        "manual": len([r for r in all_rules if r["check"] == "manual"]),
        "unverified_citations": len([r for r in all_rules if not r["citation_verified"]]),
        "scoring_formula": (
            "score = 100 x (weight of rules passed) / (weight of rules that could be scored). "
            "Rules marked REVIEW or NOT_APPLICABLE are excluded from both halves."
        ),
        "rules": all_rules,
    }


# Catch-all route to support React Router SPA navigation when frontend/dist is built
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_paths(full_path: str):
    if FRONTEND_DIST.exists():
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not found")
