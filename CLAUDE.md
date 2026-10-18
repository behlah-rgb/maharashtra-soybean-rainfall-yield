# Project: Maharashtra soybean yield vs rainfall (Group 28, mathematical modelling course)

## Goal
Estimate how monsoon rainfall (and later temperature) affects district-level soybean yield in Maharashtra, compare linear and quadratic panel models, and compute the yield change for a 100 mm rainfall deficit. Deadline: 26 Oct 2026. Two deliverables: reproducible code and a research report.

## Hard rules
1. Never edit anything in data/raw. All changes happen in scripts that write to data/interim or data/processed.
2. Never invent, estimate by hand, or hard-code a result. Every number in a table, figure or the report must come from code in src/.
3. If a check fails or the data looks wrong, STOP and tell me. Do not work around it silently.
4. Do not claim causality. Describe results as associations under the model's assumptions. Fixed effects reduce confounding by fixed district traits only.
5. No model output may go into the report unless it comes from the final gridded panel. Prototype outputs on subdivision-level rainfall are labelled "PROTOTYPE - NOT FOR THE REPORT".
6. Do not install packages I did not ask for. Do not touch files outside this repo.
7. Do not start a step beyond the one I asked for.

## Logging (mandatory)
- After every step or script, append an entry to docs/PROGRESS.md: date, what was done, WHY (the reason for any choice), result (row counts, key numbers), and any problem or deviation from docs/SPEC.md.
- Log every data decision (dropped rows, renamed districts, unit conversions, assumptions) in docs/notes.md.
- Do not rewrite earlier log entries; only append. If a decision is reversed, add a new entry saying so and why.

## Conventions
- Python, run from the repo root. Paths, seed, year range, area threshold and file names live in config.py; never hard-code them in scripts.
- Scripts in src/ are numbered and run in order. Each script reads from data/ and writes to data/ or outputs/. Keep them re-runnable from scratch.
- Rename columns by header name, never by position. Fail loudly (assert) on unexpected row counts, missing values or unmapped district names.
- Save figures to outputs/figures and tables to outputs/tables as CSV. Model summaries go to outputs/logs.
- Specification of record: docs/SPEC.md. If a change to the specification seems necessary, propose it and wait for my approval.

## Data notes
- Rainfall in the IMD file is by subdivision, not district. "MATATHWADA" is the file's spelling of Marathwada.
- ERA5 temperature file is one grid point (Konkan coast), not used in the model.
- ICRISAT districts appear to follow older boundaries; current districts need mapping to their parents.
- Zero soybean area means "not grown", not a real zero yield.