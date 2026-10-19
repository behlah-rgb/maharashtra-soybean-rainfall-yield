# maharashtra-soybean-rainfall-yield

Group 28 mathematical-modelling project: district fixed-effects regression of soybean yield on monsoon rainfall and temperature in Maharashtra, 13 districts, 2000-2017. Specification of record: `docs/SPEC.md` (with dated amendments). Submission overview: `docs/SUBMISSION_README.md`. Handoff notes: `docs/HANDOFF.md`.

## Quick start

1. **Environment** (from the repo root; developed with Python 3.14.6):
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Raw weather data.** The IMD gridded daily rainfall (0.25 deg) and Tmax/Tmin (1.0 deg) files for 2000-2017 (54 files, about 500 MB) are **not included**. `src/05a_download_weather.py` downloads them with imdlib into `data/raw/grids/imd/` (network access needed; about 1 hour, IMD's server is slow) together with the DataMeet 2011 district boundaries. Sources and checksums: `docs/data_sources.md`.
3. **Run everything** from `data/raw`:
   ```
   bash run_all.sh                  # first run: downloads the grids (05a), then builds and analyses
   bash run_all.sh --skip-download  # later runs: about 30 s; fails if the grids are missing
   bash run_all.sh --prototype      # also re-runs the historical prototype steps (03, 04 on panel_v1)
   ```
   `run_all.sh` runs, in order: 01, 02, (05a), 05, 05c, 05b, 03, 06, 07, 08, 09, 11, 10, 12, 13. It stops at the first error.

## Where outputs go

| Location | Contents |
|---|---|
| `data/interim/`, `data/processed/` | district map, crosswalk, dissolved old districts, grid weights, `panel_final.csv` (13 x 18) and `panel_final_wide.csv` (17 x 18) |
| `outputs/final/{tables,figures,logs}/` | final results (src/03, 05c, 06-09, 11); the only outputs that may feed the report |
| `outputs/tables/validation_*`, `outputs/figures/validation_*` | panel validation (src/05b) |
| `outputs/prototype/`, `outputs/tables/prototype_*`, `outputs/logs/prototype_models.txt` | historical prototype on subdivision rainfall, labelled PROTOTYPE - NOT FOR THE REPORT |
| `docs/RESULTS_SUMMARY.md`, `docs/REPORT_INPUTS.md` | generated summaries of every headline number and the report's tables/figure list |
| `report/figures_final/` | the report figures (copied by src/13) with `MANIFEST.csv` |

## Notes

- `src/06`-`09` and `src/11` require `data/processed/panel_final.csv`; they no longer run on `panel_v1.csv` (no temperature). Scripts 03 and 06-09/11 refuse to write to `outputs/final` from any other input.
- Raw files in `data/raw` are never edited. Reproducibility was checked on 2026-10-19 by deleting `data/processed` and `outputs/final` and re-running: all tables and figures came out byte-identical (`docs/PROGRESS.md`).