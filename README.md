# Legal Metrology Compliance Checker

A prototype for **SIH26034** — "Software system to check compliance of packaged commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels". You photograph the label of a pre-packaged commodity, the system reads the declarations printed on it, checks those declarations against 15 implemented rules, and produces a score, a status, a rule-by-rule breakdown and a downloadable PDF report. It was built in about 30 hours for a college internal hackathon. The guiding constraint throughout was explainability: every file is small enough that a team member can open it and explain what it does, and every finding traces back to a rule id, an observed value and a line of code.

---

## The core idea

The system is a two-stage pipeline, and the split between the stages is the whole design.

```
   +-----------------+
   |  Product image  |   phone photo, or a generated demo label
   +--------+--------+
            |
            v
   +----------------------------------------------+
   |  STAGE 1 — Gemini extraction                 |   ai_service.py
   |  "What does the package SAY?"                |
   |  image -> JSON of declarations               |
   |  anything not visible comes back as null     |
   +--------+-------------------------------------+
            |
            |  plain dict: net_quantity, mrp_text_verbatim,
            |  date_of_packing, consumer_care, image_quality, ...
            v
   +----------------------------------------------+
   |  STAGE 2 — Deterministic rule engine         |   compliance.py + rules.json
   |  "Does that satisfy the rule we             |
   |   implemented?"                              |
   |  15 rules, 4 check types, no AI, no          |
   |  randomness, temperature-free plain Python   |
   +--------+-------------------------------------+
            |
            v
   +----------------------------------------------+
   |  Score 0-100  +  status                      |
   |  COMPLIANT / NEEDS_REVIEW /                  |
   |  POTENTIAL_VIOLATION  + a written reason     |
   +--------+-------------------------------------+
            |
            v
   +----------------------------------------------+
   |  SQLite (one table, backend/compliance.db)   |   database.py
   +--------+-------------------------------------+
            |
            +---> Dashboard  (counts, average score, most common failures)
            +---> History    (every inspection, filterable by status)
            +---> Result page (photo next to what was read off it)
            +---> PDF report  (generated on request)                report.py
```

**The AI is not the legal decision maker.** Gemini is used for exactly one job in the compliance path: transcribing what is printed on the label into structured fields. It is explicitly instructed not to judge compliance, and it is instructed to return `null` rather than guess a value it cannot see. Every verdict — pass, fail, review, not applicable, the score, and the overall status — is produced by `backend/compliance.py`, which is ordinary Python matching values against rules in `backend/rules.json`.

Why it is built this way:

- **Reproducibility.** The same reading always produces the same verdict. A language model asked to "decide compliance" may not.
- **Traceability.** When a judge or an inspector asks why a package failed, the answer is a rule id, the value we looked at and the pattern it did not match — not "the model thought so".
- **Auditability.** The rules live in a JSON file that a domain expert can read and correct without touching Python.
- **Failure containment.** If the AI misreads the label, the mistake is visible on the result page, because the photo is shown right next to the extracted values.

There is a second, optional AI call (`explain_findings`) that restates the rule engine's already-final findings in one plain-language paragraph. It cannot change a verdict, and if it fails the scan still succeeds.

---

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| UI | **React 19 + Vite + TypeScript** | Vite gives instant hot reload, which matters when you have 30 hours; TypeScript mirrors the backend Pydantic models so a renamed field breaks at compile time instead of in the demo. |
| Styling | **Tailwind CSS v4** | v4 keeps design tokens in CSS (`@theme` in `src/index.css`), so the palette is defined once and there is no JS config file to keep in sync. |
| Icons | **lucide-react** | One consistent icon set, tree-shaken, no icon font. |
| API | **Python + FastAPI** | Type hints become request validation and the interactive `/docs` page for free, so the API documents itself. |
| Storage | **raw `sqlite3`, no ORM — on purpose** | An inspection is one self-contained event, so nothing needs joining. Writing the SQL by hand means every team member can explain the storage layer; an ORM would add a layer nobody has time to learn. |
| Vision / OCR | **Google Gemini, free tier** | It reads Indian package labels (mixed fonts, curved surfaces, poor lighting) far better than classical OCR, returns JSON constrained to our Pydantic schema, and costs nothing at hackathon volume. |
| PDF | **ReportLab** | Produces a real, laid-out A4 inspection report in pure Python — no headless browser to install. |
| Images | **Pillow** | Draws the four demo labels and measures uploaded images so they fit the PDF page without distortion. |

---

## Project structure

```
sih-2026-26034/
├── README.md                       this file
├── requirements.txt                backend Python dependencies, pinned to tested versions
├── .env.example                    template for the .env holding GEMINI_API_KEY
├── design.md                       the design system brief the UI was built to (tokens, motion, typography)
├── vercel.json                     Vercel 1-click full-stack deployment configuration
├── render.yaml                     Render 1-click blueprint configuration
│
├── api/
│   └── index.py                    Vercel serverless entrypoint
│
├── backend/
│   ├── main.py                     the entire FastAPI app: every endpoint, in one readable file
│   ├── compliance.py               THE RULE ENGINE. The four check types, the score, the status. No AI.
│   ├── rules.json                  the 15 implemented rules as data: reference, requirement, check type, weight, escalation flag
│   ├── ai_service.py               the only file that talks to Gemini: extract_product_data() and explain_findings()
│   ├── models.py                   Pydantic models — the data shapes, and the JSON schema Gemini must return
│   ├── database.py                 raw sqlite3: init, insert, read, dashboard aggregates
│   ├── report.py                   builds the A4 PDF compliance report with ReportLab
│   ├── seed_data.py                inserts 20 sample inspections so the dashboard is not empty
│   ├── test_compliance.py          plain-assert tests proving the rule engine is deterministic
│   ├── compliance.db               created on first run — the SQLite database file
│   ├── uploads/                    created on first run — uploaded and demo images, served at /uploads
│   └── reports/                    created on demand — generated PDFs
│
├── sample_data/
│   ├── demo_products.json          the four demo products: description, expected status, expected score, cached extraction
│   ├── generate_demo_images.py     draws the four demo label images with Pillow, defects included
│   ├── demo_images/                the generated PNG labels
│   └── legal_metrology_pc_rules_2011.pdf   the source text the rules were written from
│
└── frontend/
    ├── package.json                npm scripts and dependencies
    ├── vite.config.ts              dev server on :5173 and the /api + /uploads proxy to FastAPI
    ├── index.html                  the single HTML page React mounts into
    ├── tsconfig*.json              TypeScript compiler settings
    ├── .oxlintrc.json              lint rules (oxlint)
    ├── public/favicon.svg          the tab icon
    └── src/
        ├── main.tsx                mounts React with the router
        ├── App.tsx                 the shell: nav bar, routes, footer
        ├── api.ts                  every backend call, in one file, using plain fetch
        ├── types.ts                TypeScript mirror of backend/models.py
        ├── ui.tsx                  shared pieces: status colours, badges, buttons, bands
        ├── index.css               Tailwind v4 theme — the colour and font tokens
        └── pages/
            ├── Dashboard.tsx       what the tool is, the numbers from the database, and what it cannot do
            ├── Scan.tsx            upload a photo, or run one of the four demo products
            ├── Result.tsx          the photo beside what was read from it, then every rule and its reason
            ├── History.tsx         every inspection, newest first, filterable by status
            └── Rules.tsx           the 15 rules, how each is checked, its weight, its citation status
```

---

## Setup

Requires Python 3.11 or newer (built and tested on 3.14) and Node.js 20 or newer. Run everything from the repository root.

### The short way

One command does all of it — virtual environment, both sets of dependencies, `.env`, the demo images, the sample database, and the test suite:

```bash
bash setup.sh
```

It is safe to run more than once; each step skips itself if it is already done. On Windows use Git Bash (which ships with Git). If it fails, it stops on the step that broke and says what to do.

**If you copied this folder from another computer** — Drive, USB, a zip — run `setup.sh` before anything else. A `.venv` records the absolute path of the Python that built it, and `frontend/node_modules` contains binaries compiled for one operating system, so neither survives the move. The script detects both and rebuilds them. Everything else in the folder copies fine.

### The long way, step by step

Do this instead if you want to see each piece, or if `setup.sh` failed and you are working out why.

Create the virtual environment:

```bash
python -m venv .venv
```

Install the backend dependencies:

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Install the frontend dependencies:

```bash
cd frontend
```

```bash
npm install
```

Go back to the root:

```bash
cd ..
```

Generate the four demo label images:

```bash
.venv/Scripts/python.exe sample_data/generate_demo_images.py
```

Optionally, fill the dashboard with sample inspections:

```bash
.venv/Scripts/python.exe backend/seed_data.py
```

**On macOS and Linux** the only difference is the path to the interpreter inside the virtual environment: use `.venv/bin/python` instead of `.venv/Scripts/python.exe`, and `python3 -m venv .venv` if `python` is not Python 3 on your machine. Everything else — the `npm install`, the script paths, the uvicorn command — is identical.

---

## Configuration

Copy the template:

```bash
cp .env.example .env
```

Then open `.env` and paste a free Gemini API key from <https://aistudio.google.com/apikey> into `GEMINI_API_KEY=`.

**The key never reaches the browser.** `.env` is read only by the backend (`ai_service.py` loads `backend/.env` and then the root `.env`). The frontend never holds a key and never calls Google. It calls our own relative paths — `/api/scan`, `/api/stats` — and Vite's dev proxy forwards those to FastAPI on port 8000. Our backend is the only thing that talks to Gemini. That is also why `frontend/src/api.ts` contains no base URL and no secret.

`.env.example` also has an optional `GEMINI_MODEL` setting. The default is `gemini-3.7-flash`. If the free-tier daily quota runs out mid-demo, switch to one of the lighter fallbacks listed in the file:

- `GEMINI_MODEL=gemini-3.5-flash-lite`
- `GEMINI_MODEL=gemini-2.5-flash`

**No key is needed to run the project.** `GET /api/health` reports whether a key is present, and the UI uses that to point you at Demo Mode instead of live scanning.

---

## Running it

Two terminals. First the backend, from the repository root:

```bash
cd backend
```

```bash
../.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

Then the frontend, in a second terminal:

```bash
cd frontend
```

```bash
npm run dev
```

- App: <http://localhost:5173>
- API: <http://localhost:8000>
- Interactive API docs: <http://localhost:8000/docs> — FastAPI generates this from the Pydantic models, so you can try every endpoint from the browser, upload an image to `POST /api/scan`, and see the exact response shape. Opening <http://localhost:8000> redirects here.

The backend must be started from inside `backend/` because `main.py` imports its neighbours as top-level modules (`import ai_service`, `import database`).

---

## How the rule engine works

`backend/rules.json` holds 15 rules. Each rule names a `check` type, and each check type is one small function in `backend/compliance.py`.

| Check type | Count | What it does |
| --- | --- | --- |
| `presence` | 7 | Is the declaration there at all? Passes if the field, or any listed alternative, holds a usable value. `LM001` accepts manufacturer **or** packer **or** importer name, because the Rules accept any of the three. |
| `format` | 4 | The declaration exists — is it written in the prescribed form? A regex from the rule is matched against the value. If the value is missing entirely, the result is `NOT_APPLICABLE`, not `FAIL`, because the matching presence rule already reported the absence and failing it twice would double-count one defect. |
| `conditional_presence` | 1 | Required only when a trigger field says the rule applies. `LM012` (country of origin) is `NOT_APPLICABLE` unless an `importer_name` was detected; once one is, a missing country of origin is a `FAIL`. |
| `manual` | 3 | Cannot honestly be decided from a photograph. Always returns `REVIEW` with the text "Requires physical verification of the package". These are `LM013` (letter height in mm), `LM014` (principal display panel and prominence) and `LM015` (permitted standard pack size). |

Each rule check returns one of four results: `PASS`, `FAIL`, `REVIEW`, `NOT_APPLICABLE`.

### The score

From `_calculate_score()` in `compliance.py`:

```
score = round( 100 * (weight of rules that PASSED) / (weight of rules that could be scored) )
```

Only `PASS` and `FAIL` count as scoreable. `REVIEW` and `NOT_APPLICABLE` are excluded from **both** the numerator and the denominator, so a package is never penalised for a rule we could not honestly evaluate. If nothing was scoreable at all, the score is 0.

The weights in `rules.json` as implemented today:

- the 7 `presence` rules (`LM001`–`LM007`) weigh **2** each,
- the 4 `format` rules (`LM008`–`LM011`) and the 1 `conditional_presence` rule (`LM012`) weigh **1** each,
- the 3 `manual` rules (`LM013`–`LM015`) weigh **0**, since they are never scored.

The maximum weight is 19, but the denominator is rarely 19, because rules that do not apply drop out of it. A correct label on a domestic (non-imported) package has a scoreable weight of **18** — `LM012`, country of origin, is `NOT_APPLICABLE` without an importer — and scores 100. That is demo product 1.

The denominator shrinks further when a missing declaration makes a format rule moot. Demo product 2 has no MRP at all, so `LM006` fails on presence and `LM008` (the tax-inclusive wording) becomes `NOT_APPLICABLE` rather than failing a second time for the same absence: 15 of 17, which is 88. Demo product 4 scores 12 of 17, which is 71. Both figures come straight from the engine.

### The three statuses

`_decide_status()` distinguishes two very different kinds of failure. This is the most important decision in the project.

- **Absence of evidence → `NEEDS_REVIEW`.** A mandatory declaration was not detected. But one photograph shows one or two faces of a package, and the declaration may well be printed on a panel the camera never saw. We are not entitled to call that a violation. These rules carry `"escalates": false`.
- **Evidence of a defect → `POTENTIAL_VIOLATION`.** The declaration *is* visible and is demonstrably wrong: a price line with no "inclusive of all taxes" wording, `100 gms` instead of `100 g`, a date that names no month, an imported package with no country of origin. We can point at the defect inside the image. These rules carry `"escalates": true`.
- **`COMPLIANT`** is only returned when every automatically checkable declaration passed *and* the image was reported as good quality and fully legible. The remaining `REVIEW` items are still listed so nobody mistakes this for a clean bill of health.

Two guards sit on top of that:

**The blurry-image guard runs first.** If the extraction step reported `image_quality: "blurry"`, the status is `NEEDS_REVIEW` and nothing else is asserted. A bad photograph undermines findings in both directions — we can neither confirm compliance nor assert a defect from it. `image_quality: "partial"` or `all_declarations_legible: false` likewise downgrades an otherwise clean result to `NEEDS_REVIEW`.

**The `MISSING_MANDATORY_FOR_VIOLATION` escalation guard.** The constant is set to `3`. Giving a package the benefit of the doubt for one absent declaration is reasonable; doing it for six is not. So when **three or more** mandatory declarations are absent at once, the status escalates from `NEEDS_REVIEW` to `POTENTIAL_VIOLATION`, on the stated reasoning that "an incomplete label is a more likely explanation than a partial photograph". Below the threshold it stays `NEEDS_REVIEW`. The number is a single named constant in `compliance.py` precisely so it can be argued about and changed in one place.

---

## Demo mode

Demo mode exists because a hackathon demo cannot depend on hotel Wi-Fi or an unexhausted API quota. Four products are prepared in `sample_data/demo_products.json`:

| Demo | Label | What is wrong | Expected status | Expected score |
| --- | --- | --- | --- | --- |
| `demo-1` | Fully compliant | Nothing. Every mandatory declaration present and in the prescribed form. | `COMPLIANT` | 100 |
| `demo-2` | Missing MRP | No retail sale price anywhere on the photographed panel. | `NEEDS_REVIEW` | 88 |
| `demo-3` | Missing consumer care details | Well printed label, but no contact route for complaints. | `NEEDS_REVIEW` | 88 |
| `demo-4` | Multiple issues | Price with no tax-inclusive wording, `100 gms` instead of `100 g`, a date of `2026` with no month, and no consumer care details. | `POTENTIAL_VIOLATION` | 71 |

**Only the extraction step is cached.** When you run a demo product, the rule engine runs live, the score is computed live, the row is written to SQLite live, and the PDF is generated live — exactly as they are for a real upload. `check_compliance()` cannot tell a cached reading from a fresh one, because both arrive as the same plain dict. What is skipped is only the Gemini call.

This means demo mode works with **no API key and no internet**.

The cached readings are not fabrications. `generate_demo_images.py` draws each label from the strings in its `LABELS` dictionary, and those strings really do contain the defects the cached extraction describes — demo 4's image genuinely prints `100 gms` and `Rs 40/-`. So if a key is available you can pass `?live=true` to the demo scan endpoint, send that same image to Gemini for a real reading, and get the same result. Replacing the generated images with real photographs later needs nothing but dropping files into `sample_data/demo_images/` under the same filenames.

**Every cached result is labelled.** Rows written by demo mode are stored with `source = "demo_cached"`, and the UI renders the badge **"Demo Result"** on them with the caveat that the label reading is cached and everything after it was computed live. The PDF carries the same note. A cached reading is never presented as fresh AI output.

### Sample data (`seed_data.py`)

The dashboard and history page are meaningless with an empty database, so `backend/seed_data.py` inserts 20 sample inspections:

```bash
.venv/Scripts/python.exe backend/seed_data.py
```

To wipe the table first:

```bash
.venv/Scripts/python.exe backend/seed_data.py --reset
```

These rows are invented for demonstration, and the code says so. They are stored with `source = "seed"`, the UI badges them **"Sample Data"**, the dashboard shows an "includes sample data" note whenever any are counted (`Stats.includes_sample_data`), and their PDF reports are stamped "SAMPLE DATA — generated for demonstration, not a real inspection".

They are still internally consistent: each one is built as a label *reading* and then run through the same `check_compliance()` the live path uses, so its score, status and per-rule results are genuinely computed rather than typed in. That is what makes the dashboard's "most common violations" tally real.

---

## API endpoints

Every endpoint in `backend/main.py`. Nothing else exists.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Redirects to `/docs`. Hidden from the schema. |
| `GET` | `/api/health` | Whether a Gemini key is configured, which model is selected, how many rules loaded, and a message telling the UI whether to offer live scanning or Demo Mode. |
| `POST` | `/api/scan` | The main endpoint. Accepts an uploaded image (JPG, PNG or WEBP, max 10 MB), runs extraction → rule engine → optional explanation → database write, and returns the full inspection. |
| `GET` | `/api/demo-products` | The four prepared demo products with their descriptions, expected statuses and image URLs. Needs no key. |
| `POST` | `/api/demo-products/{demo_id}/scan` | Runs one demo product through the pipeline. `?live=false` (default) uses the cached extraction; `?live=true` sends the same image to Gemini for a genuine reading and requires a key. |
| `GET` | `/api/inspections` | History, newest first. Optional `limit` (1–500, default 100) and `status` filter. |
| `GET` | `/api/inspections/{inspection_id}` | One full inspection: the extraction, every rule check, the image URL, the explanation. |
| `GET` | `/api/inspections/{inspection_id}/report` | Generates the PDF compliance report on demand and returns it as a download. |
| `GET` | `/api/stats` | Everything the dashboard needs in one read: totals per status, compliance percentage, average score, the five most frequently failed rules, the six most recent inspections, and whether sample data is included in the numbers. |
| `GET` | `/api/rules` | The 15 rules exactly as the engine reads them, plus counts of scoreable / manual / unverified-citation rules and the scoring formula as a string. This is what the Rules page renders. |

Uploaded and demo images are served as static files at `/uploads/<filename>`.

---

## Honest limitations

These are real and we would rather state them than have them found.

1. **We do not measure font or letter height.** Rule 9 and the Second Schedule prescribe minimum letter heights in millimetres, relative to the area of the principal display panel. That cannot be derived from an arbitrary phone photograph with no scale reference. `LM013` is therefore a `manual` check that always returns "Requires physical verification of the package". This is a design decision, not an unfinished feature: inventing a millimetre measurement would be worse than admitting we cannot take one. `LM014` (principal display panel and prominence) and `LM015` (permitted standard pack size) are `manual` for the same reason.
2. **A missing declaration is not called a violation.** One photograph shows one or two panels of a package. A declaration we did not see may simply be on the back. So a small number of absent declarations yields `NEEDS_REVIEW`, not `POTENTIAL_VIOLATION`. The threshold for escalating (three) is a judgement call, not a legal standard.
3. **15 rules is a subset of the statute, not all of it.** The Rules cover exemptions, wholesale and retail packages, combination packages, e-commerce declarations, unit sale price, and much more that we did not implement. What we implemented, we implemented honestly; the Rules page shows exactly what is and is not covered.
4. **Citations are not yet verified.** Every rule in `rules.json` currently carries `"citation_verified": false`. The rule references were written from a reading of the Rules, but no team member has yet cross-checked each one against the official gazette text. Unverified references are marked with an asterisk in the PDF and flagged on the Rules page. `GET /api/rules` returns the count.
5. **The score measures completeness of readable declarations, not legality.** A score of 100 means "every declaration we can check from this photograph was present and in the prescribed form". It does not mean the package is legally compliant, and a low score does not prove that it is not.
6. **The extraction step can be wrong.** Gemini is instructed to return `null` rather than guess, and temperature is 0 so the same image gives the same reading, but a misread value produces a wrong verdict. This is why the result page shows the photograph beside the extracted table: the reading is meant to be checked by a human, not trusted blindly.
7. **This is decision support, not a legal determination.** The tool is intended to help an inspector prioritise which packages to look at physically. It has no statutory authority and does not replace inspection. The same disclaimer is printed on every PDF report.

---

## Testing

```bash
.venv/Scripts/python.exe backend/test_compliance.py
```

No pytest, no test framework — just `assert`-style checks and printed output, so anyone on the team can read the file and explain it. It exits with code 1 if anything fails.

The suite has eight sections and it proves **determinism**: these fixtures go in, these exact statuses and scores come out, every time, with no AI involved in the decision.

1. `rules.json` loads, all 15 ids are unique, every check type is one of the four we implement, every `format` rule has a pattern, and no `manual` rule carries score weight.
2. The four demo products produce their documented status **and** their documented score. The fixtures are read from `sample_data/demo_products.json`, so the products shown in the UI and the cases tested here cannot drift apart.
3. Absence of evidence versus evidence of a defect: one missing declaration gives `NEEDS_REVIEW`, a visible `250 gms` gives `POTENTIAL_VIOLATION`, three or more missing declarations escalate, a correct label scores 100 and is `COMPLIANT`.
4. A bad photograph never produces a confident finding — a blurry image can be declared neither compliant nor in violation.
5. Conditional rules only fire when they apply: country of origin is `NOT_APPLICABLE` with no importer and `FAIL` once one is named.
6. A missing value is never penalised twice: a missing MRP fails the presence rule and makes the format rule `NOT_APPLICABLE`.
7. The format patterns accept and reject the right strings — 29 cases across net quantity (`100 g` passes, `100 gms` fails), dates (`JUN 2026` passes, `2026` and `13/2026` fail), the MRP tax-inclusive wording, and consumer care contact routes.
8. Every check carries a human-readable reason, the overall status carries a reason, and manual checks are always reported as `REVIEW` and never guessed.

If you change a rule, a pattern or a weight, run this file. Section 2 will tell you immediately if you moved a demo product's documented verdict.
