# Handoff (2026-10-18)

Status (updated 2026-10-18, after the team-lead amendments): the prototype pipeline on subdivision rainfall is complete (steps 0-4), and the final-analysis scripts src/06-09 are built and tested on the prototype panel only (outputs/prototype/). The gridded build (step 5) is still a skeleton waiting for data. Nothing has been run on gridded data and outputs/final/ does not exist. report/report.md is a heading skeleton with no results. Everything from panel_v1 is labelled **PROTOTYPE - NOT FOR THE REPORT**.

## (a) What is done and which files exist

| Step | Script | Outputs |
|---|---|---|
| 0 | config.py, requirements.txt (pinned), README.md (venv line), docs/SPEC.md | .venv (local, gitignored) |
| 1 | src/01_clean_icrisat.py | data/interim/district_subdivision_map.csv, data/processed/soy_clean.csv (234 rows, 13 districts, 2000-2017), outputs/tables/icrisat_audit.csv, outputs/tables/icrisat_yield_check.csv |
| 2 | src/02_build_panel_subdivision.py | data/interim/subdivision_rainfall.csv, data/processed/panel_v1.csv (208 rows = 13 x 16, 2000-2015) |
| 3 | src/03_eda.py | outputs/tables/eda_summary_stats.csv, eda_mean_yield_by_year.csv, eda_correlation.csv, eda_outliers.csv, eda_subdivision_rainfall_context.csv; outputs/figures/eda_mean_yield_by_year.png, eda_yield_heatmap.png, eda_yield_vs_rseason.png, eda_rainfall_by_subdivision.png, eda_correlation_matrix.png |
| 4 | src/04_models_prototype.py | outputs/logs/prototype_models.txt, outputs/tables/prototype_coefficients.csv, outputs/tables/prototype_100mm_experiment.csv |
| 5 | src/05_build_panel_gridded.py | SKELETON, not run |
| 6 | docs/data_dictionary.md, this file | - |
| 6 (final) | src/06_models_final.py `<panel> <outdir>` | `<outdir>`/tables/06_models_coefficients.csv, 06_models_fit_stats.csv, 06_models_loyo_by_year.csv; logs/06_models.txt |
| 7 | src/07_diagnostics.py `<panel> <outdir>` | tables/07_diag_tests.csv, 07_diag_influence.csv, 07_diag_leave_one_district_out.csv; 5 figures 07_diag_*.png; logs/07_diag.txt |
| 8 | src/08_scenario_100mm.py `<panel> <outdir>` | tables/08_scenario_results.csv, 08_scenario_range_curve.csv, 08_scenario_district_means.csv; figures 08_scenario_range_curve.png, 08_scenario_district_effects.png; logs/08_scenario.txt |
| 9 | src/09_robustness.py `<panel> <outdir> --wide-panel <wide>` | tables/09_robust_results.csv, 09_robust_skipped.csv; figure 09_robust_forest.png; logs/09_robust.txt |
| - | src/pipeline_utils.py | shared helpers for 06-09 (CLI, outputs/final guard, headers, FE fits, bootstraps) |
| - | report/report.md | 16-section skeleton; each heading names its feeding script/output |

Also built 2026-10-18: data/processed/soy_clean_wide.csv and panel_v1_wide.csv (wider district set, A5), and the new panel column R_julsep (Jul-Sep).

Guard: 06-09 exit with "REFUSED" if the output folder is under outputs/final/ and the input is not exactly data/processed/panel_final.csv (and, for 09, the wider panel is not panel_final_wide.csv). Tested: refusals for panel_v1.csv and for a copy named panel_final.csv stored elsewhere. Outputs carry the PROTOTYPE header unless the input is panel_final.csv.

Prototype commands (as run):
```
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
17. **Back-transformed prediction (src/06).** In kg/ha, the ln models predict held-out years worse than the trend-only model (driven by 2005-2006). In ln units rainfall improves the prediction. The kg/ha model predicts better in kg/ha.
18. **Year-bootstrap vs district-bootstrap (src/08).** The district bootstrap gives narrower intervals because it keeps the year shocks fixed. The year bootstrap is the main interval. Intervals in 08 differ slightly from src/04 because 08 uses its own seeded random streams (SeedSequence(SEED).spawn(2)).
19. **src/03_eda.py is hard-wired to panel_v1.csv.** It must take a panel path and output folder (like 06-09) before it can feed sections 4 and 7 of the report.
20. **Old-to-new district pairs are UNVERIFIED** (SPEC A5). They are listed as candidates in src/05 and must stay marked UNVERIFIED until the teammate confirms them.

## (c) What I still need from my teammate

| Item | Needed detail | Feeds (src/05) |
|---|---|---|
| IMD 0.25 degree gridded daily rainfall, 2000-2017 | Raw files (.grd or NetCDF) for every year 2000-2017, plus the format/version note | `read_imd_rain_grid` -> `district_average` -> `seasonal_windows(how="sum")` -> R_season, R_early, R_late |
| ERA5-Land monthly 2m temperature (and total precipitation), 2000-2017 | NetCDF covering Maharashtra (about 15.5-22.1N, 72.6-80.9E), product type stated ("monthly averaged reanalysis") | `read_era5_land_monthly` -> `district_average` -> `seasonal_windows(how="mean")` -> T_season, T_early, T_late |
| District boundary file | Current Maharashtra district polygons (shapefile/GeoJSON/GPKG) with CRS and source | `dissolve_to_icrisat_districts` (input polygons) |
| Old-to-new district notes | For every current district, its parent ICRISAT district, and any district whose split crossed old lines (e.g. Jalna from Aurangabad + Parbhani?). Needed also for the 4 wider-set districts (Aurangabad, Ahmednagar, Nasik, Satara). All candidate pairs in src/05 are UNVERIFIED until confirmed. | `dissolve_to_icrisat_districts` (old_new_map CSV, status column) |
| Irrigation data (optional) | District-year share of soybean (or kharif) area irrigated, 2000-2017 | Not in src/05 yet; would be an extra control or a heterogeneity split in the final models |

## (d) First three things to do when the data arrives

1. **Check units and coverage before building anything.** Read the ERA5-Land `units` attributes (Kelvin; tp as m/day mean daily rate -> x 1000 x days in month), confirm IMD grid dimensions and missing-value codes, and confirm 2000-2017 is fully covered. Log everything in notes.md.
2. **Build and check the old-boundary polygons.** Write the old-to-new CSV from the notes, dissolve, assert every selected ICRISAT district has a polygon, and plot them over the grid to count cells per district.
3. **Validate the gridded rainfall against the prototype.** For 2000-2015, average the district R_season within each subdivision and correlate it with the IMD subdivision series in panel_v1.csv. A strong correlation and similar levels mean the pipeline is right. Only then write panel_final.csv and panel_final_wide.csv, and run:
   ```
   python src/06_models_final.py data/processed/panel_final.csv outputs/final
   python src/07_diagnostics.py  data/processed/panel_final.csv outputs/final
   python src/08_scenario_100mm.py data/processed/panel_final.csv outputs/final
   python src/09_robustness.py   data/processed/panel_final.csv outputs/final --wide-panel data/processed/panel_final_wide.csv
   ```
   With district-level rainfall, 09 will also run the year-FE variant (it is skipped on panel_v1).

## Decisions
Resolved 2026-10-18 by the team lead (SPEC Amendments A1-A6): district window 2000-2017; small-area rows kept + robustness; proportional timing split; packages installed; fixed 13 districts + wider set; trend specification locked.

Still waiting:
- Standard errors: year clustering does not address the within-district serial correlation found in src/07. Options: two-way clustering (district and year) or Driscoll-Kraay SEs. A SPEC change needs approval.
- Baseline yield for kg/ha conversion in src/08: currently each district's mean observed yield over the panel years.
- The report's 16 section headings were chosen by me (no list was given); please check them against the course template.
- Whether src/03_eda.py should be converted to take a panel path and output folder.
