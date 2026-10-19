# Submission README (Group 28): soybean yield, monsoon rainfall and temperature in Maharashtra

## Folder structure

```
config.py            paths, seeds, year range, thresholds, crosswalk, model settings (single source of constants)
requirements.txt     pinned Python packages            run_all.sh   runs the whole pipeline in order
src/                 numbered scripts (below) + pipeline_utils.py (shared estimation, bootstrap, guard helpers)
data/raw/            input data, never edited (IMD grids in data/raw/grids/ are downloaded by src/05a, not included)
data/interim/        district map, crosswalk, old-district polygons, grid weights, district weather, dq flags
data/processed/      soy_clean*.csv, panel_v1*.csv (prototype), panel_final.csv, panel_final_wide.csv
outputs/final/       final tables, figures, logs (the only results that may feed the report)
outputs/prototype/   historical prototype on subdivision rainfall (PROTOTYPE - NOT FOR THE REPORT)
outputs/tables, outputs/figures, outputs/logs   step 01 audit, step 04 prototype, src/05b validation
docs/                SPEC.md (specification + amendments), notes.md (data decisions), PROGRESS.md (log),
                     data_sources.md, data_dictionary.md, HANDOFF.md, RESULTS_SUMMARY.md, REPORT_INPUTS.md
report/              report.md (structure), figures_final/ (report figures + MANIFEST)
```

## Order to run

`bash run_all.sh` (first run, downloads about 500 MB) or `bash run_all.sh --skip-download` (about 30 s). Order: 01, 02, 05a, 05, 05c, 05b, 03, 06, 07, 08, 09, 11, 10, 12, 13. Steps 03 and 04 on panel_v1 are the historical prototype (`--prototype`).

## Scripts

| Script | Purpose |
|---|---|
| 01_clean_icrisat.py | Soybean area/production/yield from ICRISAT; zero area = not grown; yield check; district rule (13 districts; 17 for robustness) |
| 02_build_panel_subdivision.py | Prototype panel with IMD subdivision rainfall (2000-2015); subdivision rainfall table used for validation |
| 03_eda.py | Summary statistics, yield and rainfall figures, correlations, outliers (prototype or final panel) |
| 04_models_prototype.py | Historical prototype models on subdivision rainfall |
| 05a_download_weather.py | Downloads IMD rainfall/Tmax/Tmin grids (imdlib) and DataMeet 2011 boundaries; writes docs/data_sources.md |
| 05_build_panel_gridded.py | Crosswalk to old ICRISAT districts, fractional-overlap grid weights, district weather (R_season, R_early, R_late, R_julsep, dry_spell_max, T_season), dq_flag, panel_final.csv |
| 05b_validate_panel.py | Validation: gridded vs IMD subdivision rainfall, district normals, plausibility, collinearity, independent rainfall signals |
| 05c_diagnose_ghats.py | Raw-byte diagnosis of extreme rainfall district-years and imdlib missing-value handling |
| 06_models_final.py | M1 (linear) and M2 (quadratic) FE models in rainfall and temperature; six inference methods; linear-vs-quadratic verdict and headline rule; AIC/BIC; leave-one-year-out; trend |
| 07_diagnostics.py | Residual plots, heteroskedasticity, serial correlation, cross-sectional dependence, influence, leave-one-district-out, R-T collinearity |
| 08_scenario_100mm.py | 100 mm deficit/surplus and weak-monsoon scenarios (percent and kg/ha) with moving-block bootstrap intervals |
| 09_robustness.py | Robustness variants (data quality, boundaries, year FE, wider district set, weights, trends, windows, drought years), variance share, area-weighting analysis |
| 10_results_summary.py | Generates docs/RESULTS_SUMMARY.md (every headline number with its source file) |
| 11_sanity_checks.py | Independent recomputation of the headline, turning points, response curves, surplus symmetry |
| 12_report_inputs.py | Generates docs/REPORT_INPUTS.md (report tables and figure list) |
| 13_collect_report_figures.py | Copies the listed report figures to report/figures_final with a manifest |

## Data sources

- **Crop:** ICRISAT District Level Database extract (`data/raw/ICRISAT-District_Level_Data.csv`): soybean area (1000 ha), production (1000 t), yield (kg/ha), Maharashtra, 2000-2017, older district boundaries.
- **Rainfall and temperature:** India Meteorological Department gridded daily data via imdlib 0.3.1: rainfall 0.25 deg (Pai et al. 2014, MAUSAM 65(1)); Tmax/Tmin 1.0 deg; 2000-2017; https://imdpune.gov.in/cmpg/Griddata/.
- **Boundaries:** DataMeet maps, `Districts/Census_2011/2011_Dist` (commit b3fbbde), licence CC BY 2.5 India.
- **Validation only:** IMD subdivision rainfall 1901-2015 (`rainfall_in_india_1901-2015.csv`); district rainfall normals (`district_wise_rainfall_normal.csv`). Rejected: single-point ERA5 temperature file.
- File-level URLs, retrieval times, sizes and checksums: `docs/data_sources.md`.
