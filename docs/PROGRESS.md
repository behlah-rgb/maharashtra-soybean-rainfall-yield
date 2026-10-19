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

## 2026-10-18 - team-lead decisions recorded; packages installed
- Done: added "Amendments 2026-10-18" (A1-A6) to SPEC.md, mirrored in notes.md. Installed xarray, netCDF4, geopandas, shapely into .venv, pinned them, and tested imports (plus a geopandas reprojection/area test and a netCDF write/read roundtrip).
- Why: decisions come from the team lead, who approves spec changes. The trend specification is locked before any gridded result exists, so it cannot be tuned to the results.
- Result: requirements.txt now pins 11 packages. Extra dependencies pulled in automatically: certifi, cftime, pyogrio, pyproj.
- Problems / deviations: none.

## 2026-10-18 - src/01, src/02 updated; wider panel and R_julsep
- Done: 01 also writes soy_clean_wide.csv (13 + Aurangabad, Ahmednagar, Nasik, Satara). 02 adds R_julsep and writes panel_v1_wide.csv. Reran both.
- Why: A5 requires a wider-set robustness panel; the Jul-Sep window was not in the panel and is needed for the window robustness check. Built in 01/02 (not inside 09) so the wide panel goes through the same checks as the main one.
- Result: panel_v1.csv 208 rows (old 12 columns unchanged); panel_v1_wide.csv 272 rows = 17 x 16, no missing values.
- Problems / deviations: none.

## 2026-10-18 - src/pipeline_utils.py and the outputs/final guard
- Done: shared module for 06-09: CLI (panel, outdir), guard, headers, PanelOLS wrapper with trend options (common, none, district, year_fe) and weights, a fast within estimator for bootstraps (asserted equal to PanelOLS), LSDV prediction, AIC/BIC, effect calculation, year and district resampling.
- Why: one implementation of the model and the guard keeps 06-09 consistent. The guard compares the resolved input path with config.PANEL_FINAL_FILE, not just the file name, so a copy called panel_final.csv elsewhere is also refused.
- Result: guard tested for 06, 07, 08, 09; all REFUSED and outputs/final was never created.
- Problems / deviations: none.

## 2026-10-18 - src/06_models_final.py (prototype run)
- Done: linear and quadratic (ln yield), the same with yield in kg/ha, and trend-only references. Common trend, entity effects, year-clustered SEs. F-test on the squared term (clustered Wald with F(1, G-1), and classical F), within R2, AIC/BIC, LOYO.
- Why: two F versions because they disagree when the iid assumption fails, and the reader should see both. Trend-only references show what rainfall adds out of sample. LOYO kg/ha for ln models uses the Duan smearing factor so the back-transform is not biased low.
- Result: coefficients identical to src/04. Squared term: clustered p = 0.145, classical p = 0.011. AIC prefers quadratic (269.8 vs 274.8); BIC nearly equal (323.2 vs 324.9). LOYO RMSE ln: 0.490 linear, 0.492 quadratic, 0.525 trend-only. LOYO RMSE kg/ha: 561 / 544 / 510 (ln models are worse than trend-only in kg/ha, driven by 2005-06).
- Problems / deviations: none.

## 2026-10-18 - src/07_diagnostics.py (prototype run)
- Done: residual vs fitted, Q-Q, residuals by year and by district, Breusch-Pagan, Brown-Forsythe across districts/years, Jarque-Bera, Wooldridge AR(1) test, Pesaran CD, influence (leverage, studentized residuals, Cook's D, DFBETAS), leave-one-district-out.
- Why: Wooldridge (2002) test implemented directly (first differences, lagged FD residuals, H0 coef = -0.5, district-clustered SE), since linearmodels has no built-in. Pesaran CD added (not in the brief) because shared rainfall series make cross-sectional dependence the main inference risk.
- Result (linear): BP p = 0.0001; Brown-Forsythe years p = 0.002, districts p = 0.097; JB p = 0.023; Wooldridge F(1,12) = 14.6, p = 0.003 (serial correlation present); Pesaran CD = 12.8, p < 0.001. 13 obs above Cook's D 4/n; 1 with |student resid| > 3 (Beed 2008). Leave-one-district-out 100 mm effect ranges -11.6% to -9.2% (linear) and -14.3% to -12.1% (quadratic); Kolhapur and Sangli move it most.
- Problems / deviations: within-district serial correlation is not handled by year clustering. Flagged for decision.

## 2026-10-18 - src/08_scenario_100mm.py (prototype run)
- Done: 100 mm deficit per district/subdivision/state, weak-monsoon 90% and 80% (ILLUSTRATIVE), range curve, timing models (proportional split main, single windows sensitivity, timing_quad exploratory). Year bootstrap (main) and district bootstrap (check), 1000 reps each; percent and kg/ha.
- Why: Rbar and Ybar are held at sample values so the bootstrap reflects coefficient uncertainty only. Seeds come from SeedSequence(config.SEED).spawn(2) so the two bootstraps are independent and reproducible.
- Result: state mean, 100 mm deficit: linear -9.9% [years -16.3, -2.4]; quadratic -12.7% [-18.4, -4.4]. Timing_linear split -9.8% [-16.5, -2.0]. The quadratic effect ranges from -20.5% at 499 mm to +1.1% at 1360 mm. Runtime ~11 s.
- Problems / deviations: CIs differ slightly from src/04 because the random stream differs; documented in HANDOFF.

## 2026-10-18 - src/09_robustness.py (prototype run)
- Done: base, drop_small_area, area_weighted, wider_districts, trend_none, trend_district, year_fe (skipped: subdivision rainfall), windows Jun-Jul / Jul-Sep / Jun-Sep, drop 2009 / 2014 / 2015. Linear and quadratic each. Delta-method CI from the clustered covariance.
- Why: delta-method CIs rather than a bootstrap per variant keep runtime short; the bootstrap is in 08 for the headline results.
- Result: linear 100 mm effect range across variants -8.5% (drop 2014) to -13.2% (area weighted); base -9.9%. Quadratic -11.4% to -16.2%, except the Jun-Jul window (-24.4%). The squared term becomes significant in the wider set (p = 0.018) and with no trend (p = 0.022).
- Problems / deviations: year_fe not run (by design on panel_v1).

## 2026-10-18 - src/05 skeleton, report skeleton, docs
- Done: src/05 now lists R_julsep, the panel_final_wide.csv output, and marks every old-to-new pair UNVERIFIED with a refusal rule. report/report.md: 16 headings, each with a comment naming its script and outputs/final file; no results or prototype numbers. Updated data_dictionary.md and HANDOFF.md.
- Why: the report must only draw from outputs/final; writing the mapping now makes that traceable.
- Result: done. Nothing run on gridded data; nothing committed. Stopped here as instructed.
- Problems / deviations: the 16 headings were not specified, so I chose them; flagged for the user.

## 2026-10-19 - team-lead amendments A7-A10 recorded
- Done: SPEC.md "Amendments 2026-10-19" (A7-A10), notes.md entry.
- Why: decisions from the team lead. A7 responds to the serial-correlation and cross-sectional-dependence findings of src/07; A8 is the professor's format; A9 settles the kg/ha baseline and adds follow-ups; A10 replaces the blanket UNVERIFIED status with sourced statuses.
- Result: recorded. Implementation follows below.
- Problems / deviations: the verdict rule in A7 ("must hold across these") is read as covering district CR, wild cluster bootstrap, year CR, two-way CR, Driscoll-Kraay and MBB L = 3. MBB L = 2 and 4 are reported as sensitivity, not part of the verdict.

## 2026-10-19 - A7 inference: src/pipeline_utils.py, src/06, src/08
- Done: added COV_METHODS (year, district, two-way CR; Driscoll-Kraay), FastFE, block_draws (MBB), district draws, wild_cluster_test (WCR, exact enumeration), boot_summary. 06 now reports every SE method side by side and a linear-vs-quadratic verdict; 08 headline intervals are MBB L = 3 with L = 2, 4 and the district bootstrap as checks. All seeds in config.BOOT_SEEDS.
- Why: src/07 found serial correlation and cross-sectional dependence; MBB keeps both. Exact enumeration makes the wild p-value seed-free with 13 clusters. The verdict covers the six methods in A7; MBB L = 2/4 are sensitivity only.
- Result (prototype): verdict INCONCLUSIVE for ln and kg/ha models (squared-term p: district CR 0.0001, wild 0.006, DK 0.019 vs year CR 0.126, two-way 0.066, MBB L3 0.148). Linear b1 p under MBB L3 = 0.067. State 100 mm effect: linear -9.9% [MBB L3 -15.4, +0.8]; quadratic -12.7% [-18.5, -2.1]. Point estimates unchanged from 2026-10-18. Runtime: 06 ~1 s, 08 ~4 s.
- Problems / deviations: the headline interval for the linear 100 mm effect now includes zero in the prototype. This changes the reading of the prototype results and should be noted for the final panel.

## 2026-10-19 - A9: Duan smearing and area-weighting investigation
- Done: 06 LOYO reports kg/ha RMSE/MAE naive and smeared for log models and trend-only. 09 adds weight shares, Kish effective N, a between/within weighting decomposition, district-specific slopes and weighted leave-one-district-out (4 tables + 1 figure). 08 states the kg/ha baseline in its log, table column and figure title.
- Why: A9 asks why weighting moves the effect most; separating cross-district from over-time weighting shows which channel acts.
- Result: smearing worsens kg/ha RMSE (both versions worse than trend-only). The weighting shift comes from both channels (between-only -12.1%, within-only -11.5%, both -13.2%, base -9.9%). Kolhapur/Sangli have the only non-negative district slopes and only 5% of the weight.
- Problems / deviations: the negative-trend re-examination waits for 2016-17 (HANDOFF).

## 2026-10-19 - A10: crosswalk guard and boundary variant
- Done: config.DISTRICT_CROSSWALK with statuses; src/05 crosswalk_table() and check_crosswalk() implemented as real code (no gridded data needed) and tested with 4 cases; dissolve docstring updated. 09 adds drop_boundary_sensitive.
- Why: replaces the blanket UNVERIFIED rule with sourced statuses. The guard is "used-pair" based, so unused UNVERIFIED rows (Mumbai, renames) do not block.
- Result: guard tests pass. Boundary variant: linear -8.4%, quadratic -11.0% (base -9.9%, -12.8%).
- Problems / deviations: I added rename rows (Dharashiv, Chhatrapati Sambhajinagar, Ahilyanagar) as UNVERIFIED. They are not from the team lead. Flagged.

## 2026-10-19 - src/03 CLI; report structure A8; docs
- Done: 03 takes <panel> <outdir> with the outputs/final guard; verified its outputs are byte/pixel-identical on panel_v1; also ran into outputs/prototype. Reran 07 (outputs identical). report/report.md rewritten to the professor's structure with feeding scripts/files per subsection. README run commands, HANDOFF updated.
- Why: A8 and the team lead's request; the identical-output check shows the conversion did not change any result.
- Result: done. Nothing run on gridded data; nothing committed.
- Problems / deviations: none.

## 2026-10-19 - A11 recorded and applied
- Done: SPEC A11.1-A11.5; config.DISTRICT_CROSSWALK updated (Washim CONFIRMED, renames ALIAS_NAME_ONLY); src/05 accepts the ALIAS_NAME_ONLY status; 10 old EDA copies deleted; crosswalk compared with the teammate's Table 4.
- Why: team-lead decisions. The headline rule is fixed before gridded results so it cannot be chosen after seeing them. The docx was read with the standard library (zipfile + XML) to avoid installing pandoc or python-docx.
- Result: 1 discrepancy (Washim: the report says the parent needs tehsil-level confirmation and mentions a historical Akola/Yavatmal split; set CONFIRMED as instructed and flagged). Other pairs consistent.
- Problems / deviations: none.

## 2026-10-19 - A12.1: imdlib installed
- Done: pip install imdlib (0.3.1) into .venv; imports tested; pinned imdlib and its new dependencies (requests, urllib3, idna, charset-normalizer, pytz) in requirements.txt (17 pins).
- Why: team-lead decision A12.1. The new dependencies are pinned too, so the environment is reproducible.
- Result: OK.
- Problems / deviations: none.

## 2026-10-19 - A12.2/3: src/05a_download_weather.py
- Done: downloaded the DataMeet 2011 district layer (pinned commit) and IMD rain (0.25 deg), tmax and tmin (1.0 deg) for 2000-2017 via imdlib.load into data/raw/grids/imd/; wrote docs/data_sources.md (URL, POST data, UTC retrieval time, units, grid, size, sha256 per file).
- Why: imdlib.load is the current documented API (README quick start) and checks exact file sizes. Files went into new dedicated folders. The coverage check reads one year only (the full rain array would be about 0.9 GB).
- Result: 54/54 IMD files on the first attempt; grids cover Maharashtra (rain 930 valid cells in the state box, temperature 76). Boundary layer: 641 districts, 35 in Maharashtra.
- Problems / deviations: none. NASA POWER fallback not needed.

## 2026-10-19 - A12.3-5: src/05_build_panel_gridded.py (skeleton replaced)
- Done: name matching (stopped on 6 unmatched names; resumed after user approval), crosswalk CSV, dissolve to 26 old districts (gpkg, areas printed), guard, fractional-overlap weights, daily district means, seasonal variables, panel_final.csv and panel_final_wide.csv.
- Why: fractional overlap is used for both grids because 7 old districts contain no 1-deg cell centre; overlap weighting uses every touching cell by its share. Weather was computed for all 26 old districts so the subdivision validation can be rebuilt from full subdivisions.
- Result: panel_final 234 rows (13 x 18), panel_final_wide 306 (17 x 18); no missing values, unique keys; no missing cells and no fallbacks. R_season 198-1855 mm, T_season 25.1-29.3 deg C, dry_spell_max 5-36 days. Independent raw-byte recomputation agrees (see notes).
- Problems / deviations: the user approved 6 spelling variants and Sindhudurg -> Ratnagiri (UNVERIFIED) mid-run.

## 2026-10-19 - A12.6: src/05b_validate_panel.py
- Done: validation (a)-(e); tables outputs/tables/validation_*.csv, figures outputs/figures/validation_*.png, log outputs/logs/05b_validation.txt.
- Why: to check the gridded panel against independent sources before any model (SPEC A12.6).
- Result: (a) gridded vs IMD subdivision R_season, 2000-2015: Vidarbha r = 0.972, ratio 1.029; Marathwada 0.964, 1.020; Madhya Maharashtra 0.884, 0.925; Konkan & Goa 0.759, 0.952 (IMD includes Goa). (b) Flagged > 25% off the normals: Kolhapur 0.634 (panel), Pune 1.320, Ahmednagar 1.264 (not in panel); the other panel districts are within 0.86-1.08. (c) T_season 25.1-29.3 deg C, warmest Yeotmal/Chandrapur/Wardha (28.2-28.3), coolest Sangli/Kolhapur (25.7-26.0); Tmax > Tmin everywhere; no missing cells. (d) corr(R_season, T_season) pooled 0.062, within district -0.485; VIF <= 1.50 (within); mean cross-district rainfall correlation 0.54; participation ratio 2.56 effective signals, 5 components for 90% of variance, first component 59%. (e) 2016 mean yield 1278 kg/ha and 2017 1118 kg/ha, recovering from 606 (2014) and 592 (2015).
- Problems / deviations: Kolhapur fails the normals check; Western Ghats anomalies in the gridded rainfall (Ratnagiri/Raigad 2008, Pune/Satara 2005). Reported, not changed. Stopped before any model, as instructed; src/06-09 not run on panel_final.
