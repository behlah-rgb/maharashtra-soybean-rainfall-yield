# Progress log (append only)

Format for each entry:
## YYYY-MM-DD HH:MM - step name
- Done:
- Why:
- Result:
- Problems / deviations from SPEC.md:

## 2026-10-18 - step 0: config, requirements, README, SPEC
- Done: filled config.py (paths, file names, seed=28, years 2000-2017/2015, area threshold 20, min years 15, rainfall month windows, shock 100 mm, N_BOOT 1000, district->subdivision map). Wrote requirements.txt and the README venv line. Created .venv (gitignored) and installed only the seven requested packages. Pinned the installed versions in requirements.txt. Wrote docs/SPEC.md before fitting anything.
- Why: CLAUDE.md requires all constants in config.py. Pinned versions make the runs reproducible. Seed 28 = group number (an arbitrary but documented choice). The district map lives in config.py as the single source and is written to data/interim by src/01, so it is versioned with the code.
- Result: Python 3.14.6; pandas 3.0.6, numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0, linearmodels 7.1, matplotlib 3.11.2, seaborn 0.13.2.
- Problems / deviations: the district rule's counting window was ambiguous (2000-2017 vs 2000-2015). I chose 2000-2017, which reproduces the expected list; see notes.md. Needs the user's confirmation.

## 2026-10-18 - step 1: src/01_clean_icrisat.py
- Done: filtered to soybean columns, dropped zero-area rows, checked yield against production/area, applied the district rule, wrote soy_clean.csv, icrisat_audit.csv, icrisat_yield_check.csv and the district map.
- Why: zero area means not grown (CLAUDE.md), so keeping those rows as zero yields would bias the mean down and break ln(yield). The yield check confirms the units before any ratio is used. The rule is counted over 2000-2017 because it reproduces the expected list and describes the soybean belt in the target period (see notes.md).
- Result: 464 raw rows -> 68 zero-area rows dropped -> 13 selected districts x 18 years = 234 rows, balanced. Max yield discrepancy 0.0999 kg/ha. Selected list identical to the expected list. If counted over 2000-2015 only, Beed and Osmanabad would drop out.
- Problems / deviations: none from SPEC. Six kept rows have area < 20k ha (early-2000s Beed, Nanded, Osmanabad); see notes.md.

## 2026-10-18 - step 2: src/02_build_panel_subdivision.py
- Done: built subdivision-year Jun-Sep, Jun-Jul and Aug-Sep totals from the monthly IMD columns, joined them via the map, restricted to 2000-2015, added ln_yield and trend, and saved panel_v1.csv.
- Why: windows are built from the monthly columns so the early/late split uses the same source as the season total; the file's Jun-Sep column is used only as a check. The subdivision is re-attached from the map file (not inherited) so the map is the single join key.
- Result: 208 rows = 13 x 16, balanced, no missing values. Mean R_season 832 mm (SD 230). Mean yield 1153 kg/ha. 3 independent rainfall series.
- Problems / deviations: none.

## 2026-10-18 - step 3: src/03_eda.py
- Done: summary stats, mean yield by year (table + figure), district-by-year heatmap, yield vs R_season by subdivision, rainfall per subdivision with mean (small multiples), correlation matrix, outlier table, rainfall context table for the 100 mm shock.
- Why: the rainfall figure uses small multiples with a shared y-axis instead of three overlapping lines so each mean line stays readable. Subdivisions use 3 colours plus 3 marker shapes, so identity does not rely on colour alone. Outliers were checked on both yield and ln yield because the main outcome is the log. Every output is labelled PROTOTYPE because it comes from panel_v1. The palette validator (node) is not installed, so I used the reference palette's documented 3-slot all-pairs set without re-running it.
- Result: 0 outliers beyond 3 SD (max |z| = 2.73, Kolhapur 2005). Mean R_season: Vidarbha 961 mm (SD 190), Marathwada 622 (140), Madhya Maharashtra 801 (207). Pooled corr(ln_yield, R_season) = 0.22, corr(ln_yield, trend) = -0.29.
- Problems / deviations: none from SPEC.

## 2026-10-18 - step 4: src/04_models_prototype.py
- Done: fitted linear, quadratic, timing_linear and timing_quad PanelOLS models (district FE + trend, year-clustered SEs). Ran the clustered Wald test on the squared terms and the 100 mm experiment at each subdivision's mean rainfall, with a 1000-rep year bootstrap. Wrote outputs/logs/prototype_models.txt, outputs/tables/prototype_coefficients.csv and outputs/tables/prototype_100mm_experiment.csv, all with the PROTOTYPE header.
- Why: whole-year resampling keeps the cross-district correlation within a year (shared rainfall), matching the clustering. Bootstrap SEs of the coefficients are reported next to the clustered SEs because 16 clusters is few. The squared-term test is reported as a Wald chi2 with F = W/q, since linearmodels gives the Wald form.
- Result: within R2 = 0.236 (linear), 0.262 (quadratic), 0.237 (timing_linear), 0.376 (timing_quad). b1 (linear) = 0.00104 (cluster SE 0.00035, boot SE 0.00042). 100 mm deficit: linear -9.88% [boot 95% -16.4%, -0.9%]. Quadratic: Marathwada -17.7%, Madhya Maharashtra -13.5%, Vidarbha -9.6%. Squared term in quadratic: Wald chi2(1) = 2.36, p = 0.124. Timing_quad squares: chi2(2) = 47.4, p < 0.0001.
- Problems / deviations: no deviation from SPEC. The robustness outcome (yield in kg/ha) was NOT fitted, because step 4 of the brief listed only the ln models; it is still in SPEC for the final panel. Oddities are logged in notes.md (negative trend, implausible convex late-season term, clustered SE < bootstrap SE).

## 2026-10-18 - step 5: src/05_build_panel_gridded.py (skeleton)
- Done: function signatures + docstrings for read_era5_land_monthly, read_imd_rain_grid, dissolve_to_icrisat_districts, district_average, seasonal_windows and build_panel_final. Every body raises NotImplementedError. Syntax-checked with py_compile; NOT run.
- Why: two small helpers (district_average, seasonal_windows) were added beyond the requested list so the panel_v1 column definitions are written in one place. Packages that are not installed (xarray, geopandas) are named in the module docstring and not imported, so nothing new is installed.
- Result: n/a.
- Problems / deviations: none.

## 2026-10-18 - step 6: docs/data_dictionary.md, docs/HANDOFF.md
- Done: data dictionary for all 12 panel_v1 columns; HANDOFF with files, 13 data issues, the teammate data list mapped to src/05 functions, and the first three steps.
- Why: so the teammate's data can be plugged in without re-reading the code.
- Result: done. Stopped here as instructed; no final models, diagnostics, scenarios or report.
- Problems / deviations: none.

## 2026-10-18 - .gitignore update
- Done: replaced .gitignore with the suggested version and added .gitkeep to data/raw/grids, data/interim, data/processed, outputs/figures, outputs/tables and outputs/logs.
- Why: the old global `*.log` rule could hide model logs in outputs/; it is now limited to report/. The empty folders were not tracked, so a fresh clone lacked them. Added cache, editor and Office-lock rules. data/raw, data/processed, data/interim and outputs stay tracked (all small) so results are visible without rerunning.
- Result: check-ignore confirms .venv, *.nc, __pycache__ and report/*.log are ignored, and outputs/logs/prototype_models.txt is not. git status shows no .DS_Store, __pycache__ or .venv entries.
- Problems / deviations: none.
