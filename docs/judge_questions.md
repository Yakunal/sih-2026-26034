# Judge questions — prep sheet

SIH26034. Automated checking of packaged-commodity labels against the Legal Metrology
(Packaged Commodities) Rules, 2011, from a photograph. Built in about 30 hours.

Every answer below is checked against the code. If you are asked something not on this
sheet, say what the code does or say you do not know. Do not invent behaviour.

---

## If you only remember three things

1. **The AI reads, the rule engine decides.** Gemini answers one question — "what does the
   package say?" Every compliance finding comes from plain Python in `backend/compliance.py`
   with no model in the loop.
2. **A missing declaration is a review item; a visible defect is a violation.** One photo
   shows one or two panels, so absence of evidence is not evidence of a defect. But "100 gms"
   instead of "100 g" is a defect we can point at in the image.
3. **We do not measure millimetres from a photograph, and we say so.** Rule 9 letter height
   returns "needs physical verification" rather than a fabricated number.

---

## The architecture

### Explain your system in one minute.

A user uploads a photo of a package label. `backend/main.py` saves it, then calls
`ai_service.extract_product_data()`, which sends the image to Gemini and gets back a fixed
JSON structure of twelve declarations — manufacturer, address, net quantity, MRP, date,
consumer care, and so on. That dictionary goes into `compliance.check_compliance()`, which
runs 15 rules from `backend/rules.json` and returns a score out of 100, a status, and a
reason for every single rule. The result is written to SQLite, shown in a React UI, and can
be downloaded as a PDF from `backend/report.py`. The whole flow is the five numbered steps
in the `POST /api/scan` docstring in `backend/main.py`.

### Why one FastAPI file and raw sqlite3 instead of a layered architecture with an ORM?

Our hard design constraint was that every member of a five-person team must be able to
explain any file in the repo. A service layer, a repository layer and an ORM would have added
three indirections to a project with one table and about ten endpoints. `backend/database.py`
writes the SQL by hand, so when you ask how the database works we can show you the query.
At this scale the layering would be cost with no benefit.

### Where exactly does the AI stop and your logic start?

The AI stops at `ai_service.extract_product_data()`, which returns a plain dict. Everything
after that is deterministic Python: `compliance.check_compliance()` decides, `_calculate_score()`
scores, `database.save_inspection()` stores, `report.generate_report()` prints. There is one
other AI call, `explain_findings()`, which rewrites the already-decided findings into a
paragraph of plain English — it cannot change a verdict, and if it fails we return `None` and
the report shows the rule engine's own hand-written reasons instead.

### Why SQLite and not PostgreSQL?

An inspection is one self-contained event: one image, one extraction, one set of rule results.
Nothing is shared between inspections, so there is nothing to join, and there is exactly one
table. SQLite is a single file, `backend/compliance.db`, with zero setup, which means a judge
can clone this repo and run it in one minute. `score` and `status` are duplicated into their
own columns alongside the JSON so the dashboard can count statuses in plain SQL. Moving to
Postgres later means changing one file, `backend/database.py`.

### What happens if the Gemini API is down or the key is missing?

If the key is missing, `ai_service.is_configured()` returns false, `/api/health` tells the
frontend so, and the UI switches to Demo Mode with a banner — the whole app still works
because Demo Mode needs no key. A live upload in that state returns HTTP 503 with the actual
message "GEMINI_API_KEY is not set...", which `frontend/src/api.ts` surfaces to the user
verbatim. If the API is down, out of quota, or refuses the image, `POST /api/scan` returns
HTTP 502 with the underlying error and a pointer to Demo Mode. The optional explanation call
catches every exception and returns `None`, so a scan never fails because the summary failed.

### How is the frontend wired to the backend?

`frontend/src/api.ts` uses plain `fetch` against relative paths like `/api/scan`. The dev
proxy in `frontend/vite.config.ts` forwards `/api` and `/uploads` to `127.0.0.1:8000`. That
is why the frontend never needs the backend's address and why there is no API key anywhere in
the browser bundle — the browser only ever talks to our server, and our server is the only
thing that talks to Gemini.

---

## The AI

### How do you stop the AI from hallucinating a declaration that is not on the package?

Three things, all in `backend/ai_service.py`. First, the prompt's strongest instruction is
"If you cannot clearly see a declaration, return null for it. Do not guess, complete, or infer
a value from the brand, the product type, or common sense." Second, we do not accept free text:
`response_schema` is the `ExtractedData` Pydantic model from `backend/models.py`, so the model
is forced to return exactly those keys and every field defaults to `None`. Third, temperature
is 0. We are explicit about the risk this defends against: a model that fills in a plausible
address it never read would silently turn a non-compliant package into a compliant one.

### Is the AI deciding whether the product is legally compliant?

No. The prompt tells it "Do not judge whether the package is legally compliant. That is not
your task." Every verdict comes from `backend/compliance.py`, which contains no model, no
randomness and no learning. This matters technically because the same image must give the same
verdict when an inspector re-runs a scan. It matters legally because a finding has to be
traceable: when you ask why a package failed, we answer with a rule id, the exact value we
looked at, and a line of code — not "the model thought so."

### Why do you trust the AI's reading at all, then?

We do not trust it blindly, and this is the honest limit of the system: if Gemini misreads
the label, the rule engine will faithfully decide on a wrong reading. What we do is narrow the
job to transcription, which vision models are good at, and force the model to grade its own
photo. It reports `image_quality` as good, blurry or partial, plus
`all_declarations_legible` and `overall_confidence`. If it says blurry, `_decide_status()` in
`backend/compliance.py` refuses to assert anything and returns NEEDS_REVIEW — even when a
defect was detected. That is why we can say "needs review" instead of guessing.

### Is the output reproducible? What is the temperature?

Temperature is 0 for the extraction call. The rule engine is fully deterministic, so given the
same extraction the score, the status and all 15 rule results are identical every time —
that is what `backend/test_compliance.py` proves, 58 assertions, all passing. Be honest about
the caveat: temperature 0 makes a hosted LLM near-deterministic, not mathematically guaranteed,
and Google can change the model behind a name. The half we control, the deciding half, is
exactly reproducible.

### You send the image to Google. What about privacy?

Be straight about this. On a live scan the photo is saved locally to `backend/uploads/` and
sent over HTTPS to Google's Gemini API. We are on a free Google AI Studio key, so we cannot
promise anything about retention on Google's side, and for a real government deployment that
would not be acceptable. Demo Mode sends nothing anywhere — it uses a cached extraction, so
the whole demo works offline. For production the fix is an on-premise OCR/vision model or a
government-hosted deployment with a data agreement; the boundary is already clean, because
`ai_service.py` is the only file that talks to a model, so swapping it out touches one file.

### Which model, and what happens when the free-tier quota runs out?

Default is `gemini-3.7-flash`, set by `MODEL` in `backend/ai_service.py` and overridable with
the `GEMINI_MODEL` variable in `.env` — `.env.example` documents dropping to a lighter model
mid-demo if the daily free-tier quota runs out. The model actually used is stored per
inspection in the `model_used` column and printed on the PDF, so a report always says what
produced it. If quota is exhausted entirely, live scanning returns 502 and Demo Mode still
works, which is exactly why Demo Mode exists.

### What does the AI-written summary on the report actually do?

`explain_findings()` in `backend/ai_service.py` receives only the rule engine's finished
findings as text — never the image. Its prompt says do not add legal requirements that are not
listed, do not change any verdict, do not suggest penalties, under 80 words. Temperature 0.2.
The PDF prints it under a caption saying the findings themselves come from the rule engine,
not the AI. It is cosmetic: remove it and no verdict changes.

---

## The rule engine

### Why only 15 rules when the statute has far more?

Because we would rather implement 15 rules honestly than 60 badly in 30 hours. The 15 in
`backend/rules.json` cover the mandatory declarations of Rule 6(1) plus the form requirements
that most commonly go wrong. `rules.json` is pure data — id, reference, requirement, check
type, field, regex pattern, weight, escalates flag — so adding a rule is adding a JSON object,
with no Python change unless it needs a new check type. `GET /api/rules` publishes all 15 to
the UI, including which are implemented and which are marked manual, so nobody has to guess
what we do and do not cover.

### Walk me through one rule end to end.

Take LM008, MRP declared as inclusive of all taxes. The prompt asks Gemini for two separate
fields: `mrp`, the bare price, and `mrp_text_verbatim`, the entire price line exactly as
printed, because the wording itself is what gets checked. LM008 is `check: "format"` on
`mrp_text_verbatim` with the pattern `(?i)incl[a-z.]*\s*(of\s*)?all\s*tax`, weight 1,
`escalates: true`. If the line reads "Maximum Retail Price Rs 50.00 (inclusive of all taxes)"
it PASSes; if it reads "MRP Rs 40/-" it FAILs, and because `escalates` is true that single
FAIL makes the whole product a POTENTIAL_VIOLATION — the price is visibly on the label and
visibly not in the prescribed form. That exact case is demo product 4, and it is asserted in
section 7 of `backend/test_compliance.py`.

### What are your four check types?

They are the four functions in `backend/compliance.py` and the four keys of `CHECK_FUNCTIONS`.
`presence` — is the declaration there at all (7 rules, LM001–LM007). `format` — it is there,
is it in the prescribed form, tested with a regex (4 rules, LM008–LM011). `conditional_presence`
— required only when a trigger field says so; LM012 country of origin only applies when
`importer_name` was detected. `manual` — cannot honestly be decided from a photograph, so
always REVIEW (3 rules, LM013–LM015).

### How is the score calculated, exactly?

`_calculate_score()` in `backend/compliance.py`:
`score = 100 x (weight of rules that PASSed) / (weight of rules that could be scored)`,
rounded. Only PASS and FAIL count — REVIEW and NOT_APPLICABLE are excluded from both the top
and the bottom, so a package is never punished for a rule we could not honestly evaluate.
Presence rules weigh 2, format rules and the conditional rule weigh 1, and the three manual
rules weigh 0. For a typical domestic package the scoreable total is 18, so a fully correct
label scores 100. Demo product 2 is missing only the MRP: 2 of 17 scoreable weight lost,
15/17 = 88.

### Why is a missing declaration only NEEDS_REVIEW and not a violation?

Because a photograph shows one or two faces of a package, and the declaration may well be
printed on a panel the camera never saw. Absence of evidence is not evidence of a defect, so we
are not entitled to call it a violation. That is why every presence rule LM001–LM007 has
`escalates: false` in `rules.json`. A visible defect is different: "100 gms" instead of "100 g",
or an MRP with no tax-inclusive wording, is wrong in the image we are holding, and those rules
carry `escalates: true`. This one distinction is the core design decision of the project.

### Then when DO you report a potential violation?

Two ways, both in `_decide_status()`. One, any FAIL on a rule with `escalates: true` — the five
escalating rules are LM008 tax wording, LM009 unit symbol, LM010 month-and-year, LM011 usable
consumer contact, LM012 country of origin on an imported package. Two, the escalation guard:
the constant `MISSING_MANDATORY_FOR_VIOLATION = 3` means that when three or more mandatory
declarations are absent at once, an incomplete label becomes a more likely explanation than a
partial photograph, so we stop giving it the benefit of the doubt. Both cases print the rule
ids in `status_reason`, which is shown in the UI and on the PDF. And both are overridden by a
blurry photo, which forces NEEDS_REVIEW — a bad image cannot support a violation either.

### Can the score be high while the verdict is POTENTIAL_VIOLATION?

Yes, and that is intended. The score measures how complete and well-formed the declarations we
could read are; the status is the verdict. Take a label where all seven mandatory declarations
are present and correct but the price line reads "MRP Rs 40/-": 17 of 18 scoreable weight
passes, so the score is 94, and the status is still POTENTIAL_VIOLATION because one visible
declaration is not in the prescribed form. Non-compliance is not proportional — one defect is a
defect. That is why we surface both numbers and never let the score alone be the answer.

### Do you punish a missing declaration twice?

No, and there is a test for it. If a field is absent, its presence rule FAILs and its matching
format rule returns NOT_APPLICABLE rather than a second FAIL — see `_check_format()`, which
says explicitly that failing it twice would punish the same defect two times and distort the
score. Section 6 of `backend/test_compliance.py` asserts that a missing MRP gives LM006 = FAIL
and LM008 = NOT_APPLICABLE.

### What if the manufacturer's name is missing but the packer's is present?

The law accepts alternatives, so rules carry an `alt_fields` list and `_first_available()`
takes the first field that has a value. LM001 looks at `manufacturer_name`, then `packer_name`,
then `importer_name`, and the reason line says which alternative was accepted. There is also a
guard on junk values: `_EMPTY_VALUES` treats "-", "n/a", "none", "not visible" and similar as
nothing found, so a model that writes "N/A" instead of null does not accidentally pass a rule.

---

## Font size and measurement

### Rule 9 sets a minimum letter height in millimetres. Do you check it?

No, and we report that instead of hiding it. LM013 in `rules.json` is `check: "manual"` with
weight 0, so it always returns REVIEW with the reason "Requires physical verification of the
package; not determinable from an image." The prescribed height depends on the area of the
principal display panel and the net quantity, which is a physical measurement of the actual
package. It is counted in the "need physical verification" number on the result page and the
PDF, so an inspector knows exactly what is still owed.

### Why not just calibrate with pixel measurement?

Because there is nothing to calibrate against. An uploaded phone photo has no reference object
of known size, unknown camera distance, unknown focal length and lens distortion, and packages
are usually curved, so the same letter measures differently across the frame. Any millimetre
number we printed would be a fabricated number with a legal consequence attached. We think
returning "needs physical verification" is the stronger engineering answer: the system is
useful precisely because you can trust what it does claim. If we wanted to measure it properly,
the honest route is a fiducial marker of known size in frame, or a caliper — not a heuristic.

### Which other rules are marked manual?

Three in total. LM013, letter height under Rule 9 and the Second Schedule. LM014, Rule 7 —
whether declarations are on the principal display panel, grouped and conspicuous, which needs
the physical package because one photo shows only part of it. LM015, permitted standard pack
sizes under the Second Schedule, which needs the commodity classified against that schedule
first. All three carry weight 0, so they never move the score, and a test asserts that manual
checks are always REVIEW and never guessed.

---

## Honesty and demo mode

### Is this a live AI result or a canned demo?

Whichever we tell you it is, and the system tells you too. Every inspection row stores a
`source` of `live_ai`, `demo_cached` or `seed`, the API returns `is_demo` on every scan
response, and the PDF prints the source in words — for example "DEMO — cached extraction, live
rule engine (not a fresh AI analysis)". If a key is configured, each demo product also has a
"Run live" button that sends the same image to Gemini for a genuine reading, and we are happy
to press it in front of you.

### What exactly is cached in demo mode?

Only the extraction step — the answer to "what does the label say?". The rule engine, the
scoring, the status decision, the SQLite write and the PDF all run live, exactly as they do
for a real upload. `check_compliance()` cannot tell the difference between a cached dict and a
fresh one, which is why demo mode is honest rather than a mock. And the cached readings are not
invented: `sample_data/generate_demo_images.py` draws the label images, so demo product 4
really does print "100 gms", "Rs 40/-" and "2026" — the cached extraction is a recording of a
real reading of that same image.

### Where did the 20 inspections in your dashboard come from?

`backend/seed_data.py` inserts 20 invented sample inspections so the dashboard and history page
have something to show. They are labelled honestly: `source = 'seed'`, the dashboard shows an
"Includes sample data" note driven by the `includes_sample_data` flag from
`database.get_stats()`, and their PDFs are stamped "SAMPLE DATA — generated for demonstration,
not a real inspection". They are internally consistent, though: each is written as a label
reading and then run through the same `check_compliance()` the live path uses, so the scores,
statuses and the dashboard's "most common violations" tally are genuinely computed, not typed
in by hand.

### Are your legal citations verified?

Not yet, and the code says so. Every rule in `rules.json` carries
`"citation_verified": false`, all 15 of them. `GET /api/rules` returns an
`unverified_citations` count, the Rules page shows it, and the PDF puts an asterisk next to
each reference with a footnote saying the citation has not been cross-checked against the
official gazette text. The requirement text is our plain-language reading of the Rules; the
sub-clause numbering is the part that still needs a lawyer or the gazette PDF. We built the
flag in on purpose rather than discovering it in front of you.

---

## Testing, limits, and future work

### How do you know the rule engine is correct?

Run `python backend/test_compliance.py`. It is 58 assertions and no test framework — just
prints and asserts, so anyone can read it. It checks that all 15 rules load and are well
formed, that the four demo products produce their documented status and exact score (100, 88,
88, 71), that one missing declaration gives NEEDS_REVIEW while "250 gms" gives
POTENTIAL_VIOLATION, that three or more missing declarations escalate, that a blurry image can
never produce either a COMPLIANT or a violation verdict, that LM012 stays NOT_APPLICABLE until
an importer appears, and that each regex accepts and rejects the right strings. The demo
fixtures are read from `sample_data/demo_products.json`, so what the UI shows and what the
tests assert cannot drift apart. All 58 pass.

### What is NOT tested?

The AI. There is no test of extraction accuracy, because we have no labelled set of real
photographs to measure it against. There are also no HTTP-level tests of `main.py`, no frontend
tests, and no PDF snapshot test. What is tested is the part that makes the decisions.

### What are the biggest weaknesses of this system?

Five, honestly. One, extraction accuracy is unmeasured — if Gemini misreads a label, the rule
engine confidently decides on a wrong reading. Two, 15 rules is a subset of the statute, and
three of them we do not evaluate at all. Three, the format checks are regexes, so they
approximate legal form rather than embody it — LM011 accepts any run of eight or more
digit-like characters as a contact number, so a long batch code could pass it. Four, one
inspection is one image, so we cannot merge the front and back panels of the same package.
Five, `overall_confidence` is stored and displayed but never used in the status decision, so a
0.4-confidence reading and a 0.95 reading are treated alike unless the model also flagged the
image as blurry or partial. There is also no authentication, no rate limiting, and one SQLite
file — fine for a prototype, not for a field deployment.

### What would you build next, given more time?

In order. First, a labelled set of real photographs of real packages, so we can put a number on
extraction accuracy instead of asserting it. Second, multi-image inspections, so front, back and
side panels form one verdict and "missing declaration" becomes a much stronger finding. Third,
get the 15 citations verified against the gazette and flip `citation_verified` to true, then add
the Second Schedule commodity table so LM015 stops being manual. Fourth, use
`overall_confidence` in the status decision with a threshold we can defend. Fifth, a fiducial
marker workflow so Rule 9 letter height can actually be measured rather than deferred.

### Is this ready for a real Legal Metrology officer to use?

No, and the PDF says so in its own disclaimer: this is automated decision support and does not
replace official inspection or legal determination. It is genuinely useful today as a
pre-screening and triage tool — it can tell an officer which packages out of a hundred deserve
a physical look, and it produces a report with a per-rule audit trail. To become something an
officer could rely on it would need measured extraction accuracy on real photographs, gazette-
verified citations, the missing rules implemented, a multi-panel capture workflow, an
authenticated multi-user deployment with an audit log, a data-handling arrangement that does
not send images to a third-party API, and sign-off from the Legal Metrology department itself.

---

## Questions we do NOT have a good answer to yet

Saying this is better than bluffing. If a judge pushes on any of these, concede the point and
say what we would do.

1. **What is your extraction accuracy?** We do not know. We have no labelled test set of real
   photographs, so we have no precision or recall for the reading step. The 58 tests measure the
   rule engine, not the AI.
2. **Are the citations right?** All 15 are `citation_verified: false`. We are confident about
   the substance of Rule 6(1); we have not verified every sub-clause letter against the gazette.
3. **Why is the escalation threshold 3?** It is a considered judgement, not a calibrated one.
   We have no data telling us that three missing declarations is the right place to stop giving
   a package the benefit of the doubt.
4. **Why is confidence recorded but not used?** We did not have a defensible threshold, so we
   chose to record it and not act on it rather than invent a cutoff. It is a gap.
5. **Have the regexes been validated against real Indian label text?** Only against our own
   test strings. We have not run them over a corpus of real price lines and quantity
   declarations, where abbreviations and layouts vary a lot more.
6. **What about a package whose declarations are in a regional script?** We have not tested
   any non-English label. We do not know how the extraction behaves.
7. **Can the system be fooled deliberately?** Probably. There is no check that the upload is
   even a package, no authentication, and no rate limiting.
8. **Has anyone qualified reviewed the output?** No lawyer and no Legal Metrology officer has
   reviewed our findings. That is the single most valuable next review we could get.
