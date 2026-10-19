# maharashtra-soybean-rainfall-yield

Group 28 mathematical-modelling project: regression of district-level soybean yield on monsoon rainfall in Maharashtra. Specification of record: `docs/SPEC.md`. Handoff notes: `docs/HANDOFF.md`.

Setup (from the repo root): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Run the scripts in order from the repo root:

```
python src/01_clean_icrisat.py
python src/02_build_panel_subdivision.py
python src/03_eda.py           data/processed/panel_v1.csv outputs/prototype
python src/04_models_prototype.py
python src/05a_download_weather.py   # IMD grids via imdlib + DataMeet boundaries (network; ~1 h)
python src/05_build_panel_gridded.py
python src/05b_validate_panel.py
python src/05c_diagnose_ghats.py
python src/06_models_final.py  data/processed/panel_v1.csv outputs/prototype
python src/07_diagnostics.py   data/processed/panel_v1.csv outputs/prototype
python src/08_scenario_100mm.py data/processed/panel_v1.csv outputs/prototype
python src/09_robustness.py    data/processed/panel_v1.csv outputs/prototype --wide-panel data/processed/panel_v1_wide.csv
```

Since 2026-10-19 (SPEC A13) src/06-09 use the temperature models and run on the final panel only:

```
python src/03_eda.py            data/processed/panel_final.csv outputs/final
python src/06_models_final.py   data/processed/panel_final.csv outputs/final
python src/07_diagnostics.py    data/processed/panel_final.csv outputs/final
python src/08_scenario_100mm.py data/processed/panel_final.csv outputs/final
python src/09_robustness.py     data/processed/panel_final.csv outputs/final --wide-panel data/processed/panel_final_wide.csv
python src/10_results_summary.py   # writes docs/RESULTS_SUMMARY.md from outputs/final tables
```

For the final analysis, replace `panel_v1.csv` with `panel_final.csv` (and `panel_v1_wide.csv` with `panel_final_wide.csv`) and `outputs/prototype` with `outputs/final`. Scripts 03 and 06-09 refuse to write to `outputs/final` from any other input.
