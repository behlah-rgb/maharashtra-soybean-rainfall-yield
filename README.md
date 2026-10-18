# maharashtra-soybean-rainfall-yield

Group 28 mathematical-modelling project: regression of district-level soybean yield on monsoon rainfall in Maharashtra. Specification of record: `docs/SPEC.md`. Handoff notes: `docs/HANDOFF.md`.

Setup (from the repo root): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Run the scripts in order from the repo root, e.g. `python src/01_clean_icrisat.py`, then `02`, `03`, `04`. `src/05_build_panel_gridded.py` is a skeleton and waits for the gridded data.
