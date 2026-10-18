# Handoff (2026-10-18)

Status: the prototype pipeline on subdivision rainfall is complete (steps 0-4). The gridded build (step 5) is a skeleton waiting for data. No final models, diagnostics, scenarios or report text have been started. Everything from steps 2-4 is labelled **PROTOTYPE - NOT FOR THE REPORT**.

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

## (c) What I still need from my teammate

| Item | Needed detail | Feeds (src/05) |
|---|---|---|
| IMD 0.25 degree gridded daily rainfall, 2000-2017 | Raw files (.grd or NetCDF) for every year 2000-2017, plus the format/version note | `read_imd_rain_grid` -> `district_average` -> `seasonal_windows(how="sum")` -> R_season, R_early, R_late |
| ERA5-Land monthly 2m temperature (and total precipitation), 2000-2017 | NetCDF covering Maharashtra (about 15.5-22.1N, 72.6-80.9E), product type stated ("monthly averaged reanalysis") | `read_era5_land_monthly` -> `district_average` -> `seasonal_windows(how="mean")` -> T_season, T_early, T_late |
| District boundary file | Current Maharashtra district polygons (shapefile/GeoJSON/GPKG) with CRS and source | `dissolve_to_icrisat_districts` (input polygons) |
| Old-to-new district notes | For every current district, its parent ICRISAT district, and any district whose split crossed old lines (e.g. Jalna from Aurangabad + Parbhani?) | `dissolve_to_icrisat_districts` (old_new_map CSV) |
| Irrigation data (optional) | District-year share of soybean (or kharif) area irrigated, 2000-2017 | Not in src/05 yet; would be an extra control or a heterogeneity split in the final models |

## (d) First three things to do when the data arrives

1. **Check units and coverage before building anything.** Read the ERA5-Land `units` attributes (Kelvin; tp as m/day mean daily rate -> x 1000 x days in month), confirm IMD grid dimensions and missing-value codes, and confirm 2000-2017 is fully covered. Log everything in notes.md.
2. **Build and check the old-boundary polygons.** Write the old-to-new CSV from the notes, dissolve, assert every selected ICRISAT district has a polygon, and plot them over the grid to count cells per district.
3. **Validate the gridded rainfall against the prototype.** For 2000-2015, average the district R_season within each subdivision and correlate it with the IMD subdivision series in panel_v1.csv. A strong correlation and similar levels mean the pipeline is right. Only then write panel_final.csv and move to the final models.

## Decisions waiting for the user
- Confirm the district rule window (2000-2017, current) - see (b)1.
- How to apply the 100 mm deficit in the timing models (each window separately, as now, or a split).
- Whether to install xarray/netCDF4/geopandas/shapely (needed for src/05; not installed).
- Whether the small-area early years (b)3 should be kept, or dropped in a sensitivity check.
