# Handoff (2026-10-18)

Status (updated 2026-10-19, after amendments A7-A10): the prototype pipeline on subdivision rainfall is complete (steps 0-4). src/03 and src/06-09 take a panel path and output folder, and have been run on the prototype panel only (outputs/prototype/). The gridded build (step 5) is still a skeleton waiting for data, except the crosswalk guard (implemented and tested). Nothing has been run on gridded data and outputs/final/ does not exist. report/report.md follows the professor's structure (A8) and holds no results. Everything from panel_v1 is labelled **PROTOTYPE - NOT FOR THE REPORT**.

## (a) What is done and which files exist

| Step | Script | Outputs |
|---|---|---|
| 0 | config.py, requirements.txt (pinned), README.md (venv line), docs/SPEC.md | .venv (local, gitignored) |
| 1 | src/01_clean_icrisat.py | data/interim/district_subdivision_map.csv, data/processed/soy_clean.csv (234 rows, 13 districts, 2000-2017), outputs/tables/icrisat_audit.csv, outputs/tables/icrisat_yield_check.csv |
| 2 | src/02_build_panel_subdivision.py | data/interim/subdivision_rainfall.csv, data/processed/panel_v1.csv (208 rows = 13 x 16, 2000-2015) |
| 3 | src/03_eda.py `<panel> <outdir>` (CLI since 2026-10-19; older copies remain in outputs/tables and outputs/figures) | `<outdir>`/tables/eda_summary_stats.csv, eda_mean_yield_by_year.csv, eda_correlation.csv, eda_outliers.csv, eda_subdivision_rainfall_context.csv; outputs/figures/eda_mean_yield_by_year.png, eda_yield_heatmap.png, eda_yield_vs_rseason.png, eda_rainfall_by_subdivision.png, eda_correlation_matrix.png |
| 4 | src/04_models_prototype.py | outputs/logs/prototype_models.txt, outputs/tables/prototype_coefficients.csv, outputs/tables/prototype_100mm_experiment.csv |
| 5 | src/05_build_panel_gridded.py | SKELETON, not run |
| 6 | docs/data_dictionary.md, this file | - |
| 6 (final) | src/06_models_final.py `<panel> <outdir>` | `<outdir>`/tables/06_models_coefficients.csv, 06_models_se_comparison.csv, 06_models_fit_stats.csv, 06_models_linear_vs_quadratic.csv, 06_models_loyo_by_year.csv; logs/06_models.txt |
| 7 | src/07_diagnostics.py `<panel> <outdir>` | tables/07_diag_tests.csv, 07_diag_influence.csv, 07_diag_leave_one_district_out.csv; 5 figures 07_diag_*.png; logs/07_diag.txt |
| 8 | src/08_scenario_100mm.py `<panel> <outdir>` | tables/08_scenario_results.csv, 08_scenario_range_curve.csv, 08_scenario_district_means.csv; figures 08_scenario_range_curve.png, 08_scenario_district_effects.png; logs/08_scenario.txt |
| 9 | src/09_robustness.py `<panel> <outdir> --wide-panel <wide>` | tables/09_robust_results.csv, 09_robust_skipped.csv, 09_robust_weight_shares.csv, 09_robust_weighting_decomposition.csv, 09_robust_district_slopes.csv, 09_robust_weighted_leave_one_district_out.csv; figures 09_robust_forest.png, 09_robust_area_weighting.png; logs/09_robust.txt |
| - | src/pipeline_utils.py | shared helpers for 06-09 (CLI, outputs/final guard, headers, FE fits, bootstraps) |
| - | report/report.md | 16-section skeleton; each heading names its feeding script/output |

Also built 2026-10-18: data/processed/soy_clean_wide.csv and panel_v1_wide.csv (wider district set, A5), and the new panel column R_julsep (Jul-Sep).

Guard: 03 and 06-09 exit with "REFUSED" if the output folder is under outputs/final/ and the input is not exactly data/processed/panel_final.csv (and, for 09, the wider panel is not panel_final_wide.csv). Tested: refusals for panel_v1.csv and for a copy named panel_final.csv stored elsewhere. Outputs carry the PROTOTYPE header unless the input is panel_final.csv.

Prototype commands (as run):
```
python src/03_eda.py          data/processed/panel_v1.csv outputs/prototype
python src/06_models_final.py data/processed/panel_v1.csv outputs/prototype
python src/07_diagnostics.py  data/processed/panel_v1.csv outputs/prototype
python src/08_scenario_100mm.py data/processed/panel_v1.csv outputs/prototype
python src/09_robustness.py   data/processed/panel_v1.csv outputs/prototype --wide-panel data/processed/panel_v1_wide.csv
```

Logs: docs/PROGRESS.md (per step), docs/notes.md (data decisions).

Reproduce: `source .venv/bin/activate` then `python src/01_clean_icrisat.py`, then 02, 03, 04 (about 30 s for 04).

## (b) Data issues and oddities found

1. **District rule counting window.** Counted over 2000-2017, the rule gives the expected 13 districts. Counted over 2000-2015 only, Beed (13 qualifying years) and Osmanabad (14) drop out. 2000-2017 is used. Needs confirmation.
2. **Borderline exclusions.** Aurangabad, Ahmednagar, Nasik and Satara each have 14 qualifying years, one short.
3. **Small-area early years kept.** Beed 2000-2002, Nanded 2000 and Osmanabad 2000-2001 have area < 20k ha (3.3-17.7k) but stay in the panel, because the rule selects districts, not rows.
4. **Zero area.** 68 rows (all of Konkan: Bombay, Raigad, Ratnagiri, Thane). Production and yield are also 0. Dropped as not grown. Bombay has only 14 years in the raw file.
5. **Yield consistency.** Reported yield = 1000 * production / area to within 0.1 kg/ha. Units confirmed as 1000 ha, 1000 tons, kg/ha.
6. **Only three rainfall series.** Districts in a subdivision share one IMD series: Vidarbha 7 districts, Marathwada 4, Madhya Maharashtra 2. Rainfall variation is 3 x 16, not 13 x 16.
7. **IMD ends 2015.** ICRISAT 2016-2017 cannot be used in the prototype.
8. **Bad years at the end.** Yields collapse in 2014-2015 (and 2008-2009). This gives a negative trend in every prototype model (-0.023 to -0.034 ln points/yr). The trend is sensitive to the window end; 2016-2017 in the final panel may change it.
9. **Timing quadratic looks overfitted.** The R_late term is convex (minimum at 378 mm), implying a late deficit raises Marathwada yield. Year-clustered SEs are much smaller than the year-bootstrap SEs for this model.
10. **No outliers beyond 3 SD** within district (max |z| = 2.73, Kolhapur 2005 on ln yield).
11. **ERA5 point file rejected.** It is a single point at 19.0N, 73.3E (Konkan coast), hourly 2000-01-02 to 2017-12-31, in Kelvin. It has no district variation and lies outside the soybean belt.
12. **district_wise_rainfall_normal.csv not used.** It has long-run normals only and no yearly values.
13. ICRISAT districts use older boundaries (e.g. Akola includes today's Washim). Gridded data must be averaged over the old boundaries.
14. **Inference assumptions fail in the prototype (src/07).** Residuals show strong cross-sectional dependence (Pesaran CD large, p < 0.001) and serial correlation within districts (Wooldridge test rejects). Year clustering handles the first but not the second. See "Decisions waiting".
15. **Heteroskedasticity.** Breusch-Pagan rejects; residual variance differs across years. Clustered SEs are robust to it, but area weighting changes the estimate noticeably (see 16).
16. **Area weighting moves the estimate** (src/09): the linear 100 mm effect goes from about -10% to about -13% when weighted by area. Weighting gives more weight to the large-area districts (mainly Vidarbha and Marathwada); why the estimate moves has not been examined yet.
17. **Back-transformed prediction (src/06, A9).** In kg/ha, the ln models predict held-out years worse than the trend-only model, with or without Duan smearing; smearing makes it worse (linear 541 -> 561 kg/ha RMSE, trend-only 502 -> 510). In ln units rainfall improves the prediction. The kg/ha (level) models beat the trend-only model.
18. **Bootstrap schemes (src/06, src/08, A7).** Headline = moving-block bootstrap over years (L = 3). The district bootstrap gives narrower intervals because it keeps the year shocks fixed. 08 intervals differ from src/04 (different scheme and seeds; seeds now in config.BOOT_SEEDS).
19. **Headline linear interval includes zero (prototype).** With MBB L = 3 the linear 100 mm effect is -9.9% [-15.4, +0.8] at state level; the linear rainfall coefficient p = 0.067. With L = 4 it excludes zero.
20. **Linear vs quadratic is INCONCLUSIVE (prototype).** The squared term is significant with district-clustered SEs, the wild bootstrap and Driscoll-Kraay, but not with year-clustered, two-way or MBB.
21. **Area weighting (A9).** Two channels, both matter: cross-district (district mean area) and over-time (area grows, so later years get 62.8% of the weight). Kolhapur and Sangli, the only districts with non-negative district-specific slopes, get 5% of the weight. Kish effective N = 11.0 of 13. No single district drives the shift.
22. **Crosswalk statuses (A10).** CONFIRMED_OFFICIAL_PAGE pairs rest on the teammate's citation of official pages, not independently verified. CAVEAT: Washim -> Akola (taluka-level confirmation needed); Partur taluka of Jalna came from Parbhani, so a whole-district dissolve of Jalna into Aurangabad leaves Partur out of old Parbhani. UNVERIFIED: Mumbai City/Suburban -> Bombay, and three 2023-24 renames I added (Dharashiv, Chhatrapati Sambhajinagar, Ahilyanagar). The guard blocks only if an UNVERIFIED pair is used.
23. **Negative trend (A6, A9).** Must be re-examined once 2016-2017 are in panel_final.

## (c) What I still need from my teammate

| Item | Needed detail | Feeds (src/05) |
|---|---|---|
| IMD 0.25 degree gridded daily rainfall, 2000-2017 | Raw files (.grd or NetCDF) for every year 2000-2017, plus the format/version note | `read_imd_rain_grid` -> `district_average` -> `seasonal_windows(how="sum")` -> R_season, R_early, R_late |
| ERA5-Land monthly 2m temperature (and total precipitation), 2000-2017 | NetCDF covering Maharashtra (about 15.5-22.1N, 72.6-80.9E), product type stated ("monthly averaged reanalysis") | `read_era5_land_monthly` -> `district_average` -> `seasonal_windows(how="mean")` -> T_season, T_early, T_late |
| District boundary file | Current Maharashtra district polygons (shapefile/GeoJSON/GPKG) with CRS and source | `dissolve_to_icrisat_districts` (input polygons) |
| Old-to-new district notes | For every current district, its parent ICRISAT district, and any district whose split crossed old lines (e.g. Jalna from Aurangabad + Parbhani?). Needed also for the 4 wider-set districts (Aurangabad, Ahmednagar, Nasik, Satara). Statuses per config.DISTRICT_CROSSWALK (A10). Still needed: taluka-level confirmation for Washim -> Akola; whether the boundary file uses the renamed districts (Dharashiv, Chhatrapati Sambhajinagar, Ahilyanagar); Mumbai City/Suburban -> Bombay. | `dissolve_to_icrisat_districts` (old_new_map CSV, status column) |
| Irrigation data (optional) | District-year share of soybean (or kharif) area irrigated, 2000-2017 | Not in src/05 yet; would be an extra control or a heterogeneity split in the final models |

## (d) First three things to do when the data arrives

1. **Check units and coverage before building anything.** Read the ERA5-Land `units` attributes (Kelvin; tp as m/day mean daily rate -> x 1000 x days in month), confirm IMD grid dimensions and missing-value codes, and confirm 2000-2017 is fully covered. Log everything in notes.md.
2. **Build and check the old-boundary polygons.** Run check_crosswalk() (src/05) on the boundary file's district names, log every CAVEAT row used, then dissolve, assert every selected ICRISAT district has a polygon, and plot them over the grid to count cells per district.
3. **Validate the gridded rainfall against the prototype.** For 2000-2015, average the district R_season within each subdivision and correlate it with the IMD subdivision series in panel_v1.csv. A strong correlation and similar levels mean the pipeline is right. Only then write panel_final.csv and panel_final_wide.csv, and run:
   ```
   python src/06_models_final.py data/processed/panel_final.csv outputs/final
   python src/07_diagnostics.py  data/processed/panel_final.csv outputs/final
   python src/08_scenario_100mm.py data/processed/panel_final.csv outputs/final
   python src/09_robustness.py   data/processed/panel_final.csv outputs/final --wide-panel data/processed/panel_final_wide.csv
   ```
   Also `python src/03_eda.py data/processed/panel_final.csv outputs/final`. With district-level rainfall, 09 will also run the year-FE variant (it is skipped on panel_v1). Then re-examine the trend with 2016-2017 included (A6, A9).

## Decisions
Resolved 2026-10-18 by the team lead (SPEC Amendments A1-A6): district window 2000-2017; small-area rows kept + robustness; proportional timing split; packages installed; fixed 13 districts + wider set; trend specification locked.

Resolved 2026-10-19 (A7-A10): inference methods and verdict rule; report structure; kg/ha baseline and smearing; crosswalk statuses; Pesaran kept; src/03 converted.

Still waiting:
- Verdict rule scope: I included district CR, wild bootstrap, year CR, two-way CR, Driscoll-Kraay and MBB L = 3, with MBB L = 2/4 as sensitivity only. Confirm.
- The rename rows I added to the crosswalk (UNVERIFIED) need the team lead's or teammate's confirmation.
- The old outputs/tables/eda_* and outputs/figures/eda_* copies (pre-CLI) are duplicates of outputs/prototype; delete or keep?
