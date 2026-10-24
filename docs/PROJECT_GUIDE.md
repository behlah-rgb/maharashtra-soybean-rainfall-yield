# Project guide: soybean yield, monsoon rainfall and temperature in Maharashtra (Group 28)

Written 2026-10-20 as a study guide for the oral exam. It describes the repository as it stands. It changes nothing.
Every number in this guide is quoted from a file in the repo, and the file is named next to it. Where something could not be checked, the guide says **not verified**.

---

## 0. How to read this guide

### A 30-minute reading order

| Minutes | Read | Why |
|---|---|---|
| 0-5 | Section 0 summary and Section 1 (the story) | the question, the idea of a panel regression, what the 100 mm experiment means |
| 5-10 | Section 2 (repo map) and Section 4 (data lineage diagram) | where everything lives and how data flows |
| 10-20 | Section 3, only for `05_build_panel_gridded.py`, `06_models_final.py`, `08_scenario_100mm.py`, `09_robustness.py` | the four scripts that produce the headline |
| 20-25 | Section 5 glossary entries for fixed effects, within estimator, clustered SE, moving-block bootstrap, participation ratio | the concepts you will be asked about |
| 25-30 | Section 10 (twenty questions) and Section 9 (limitations) | rehearse answers |

Then read the rest when you have time.

### One-paragraph summary

**Question:** how are June-September (monsoon) rainfall and temperature associated with district-level soybean yield in Maharashtra? Is a linear or a quadratic model better? What yield change goes with a 100 mm rainfall deficit? (`docs/SPEC.md`; `report/report.md` section 1.1.)
**Data:** ICRISAT district soybean yields (`data/raw/ICRISAT-District_Level_Data.csv`). IMD gridded daily rainfall (0.25 degree) and Tmax/Tmin (1 degree), downloaded with `imdlib` (`docs/data_sources.md`). DataMeet 2011 Census district boundaries. Together these give a balanced panel of 234 district-years (13 districts x 18 years, 2000-2017) (`docs/RESULTS_SUMMARY.md`).
**Method:** log yield is regressed on centred rainfall and temperature (linear model M1, quadratic model M2), with district fixed effects and a common linear trend (`src/06_models_final.py`). Inference uses six methods that allow for dependence. The headline intervals come from a moving-block bootstrap over years.
**Headline:** the linear-vs-quadratic verdict is QUADRATIC SUPPORTED, so M2 is the headline model. With temperature held at each district's mean, a 100 mm deficit goes with **-10.04% yield [moving-block 95% interval -15.18%, -4.29%]**, or -117.2 kg/ha [-176.6, -50.7], averaged over the 13 districts (`docs/RESULTS_SUMMARY.md`, from `outputs/final/tables/08_scenario_results.csv`).
**Main caveat:** most rainfall variation is shared by all districts in a year. Year dummies explain 0.562 of the within-district rainfall variance (`outputs/final/tables/09_robust_variance_share.csv`). With year fixed effects the M2 effect is -3.20% [-8.39%, +0.64%] (`outputs/final/tables/09_robust_results.csv`). So the headline describes state-wide monsoon variation, and it is an association, not a causal effect.

---

## 1. The story in plain language

**Why rainfall affects yield.** Soybean in Maharashtra is a rainfed crop of the monsoon (kharif) season. Plants need water to establish after sowing and to fill pods later. Too little rain stresses the crop. Very heavy rain can waterlog fields or bring disease, so the benefit of extra rain can level off or reverse. Temperature also matters, because heat stresses plants and raises water demand. (`report/report.md` sections 1.1-1.2; the agronomy itself is **not verified** by any code here.)

**What a panel regression is.** A *panel* is a dataset that follows the same units (here 13 districts) over several periods (here 18 years). Each row is one district in one year (a "district-year"). A *regression* fits an equation that explains an outcome (log yield) with explanatory variables (rainfall, temperature). A panel regression uses both kinds of variation: differences between districts, and changes over time within each district.

**What district fixed effects do.** A *fixed effect* is a separate intercept (constant) for each district, written alpha_d. It soaks up everything about a district that does not change over the years: soil, typical farming practice, average climate, irrigation share if stable. After fixed effects, the model learns only from how a district's yield moves when its own weather moves away from its own average. This is why the comparison is "Akola in a dry year vs Akola in a wet year", not "Akola vs Kolhapur".

**What the trend does.** The term gamma * t, with t = year - 2000, allows a common straight-line drift in log yield over time. It absorbs slow changes such as technology or prices, so they are not wrongly credited to weather. It is not interpreted as a technology effect (`report/report.md` section 1.5).

**Why compare linear and quadratic.** A linear model (M1) says every extra 100 mm changes log yield by the same amount. A quadratic model (M2) adds squared terms, so the effect of extra rain can shrink as rainfall grows (diminishing returns) and eventually turn negative. The project tests whether the squared terms are needed. It does not assume they are. The decision rule was fixed in advance (SPEC A11.1, A13.2).

**What the 100 mm experiment means.** Take each district at its average rainfall and temperature. Lower its rainfall by 100 mm and keep temperature fixed. Ask the fitted model how much log yield changes, convert that to a percent change and to kg/ha, and average over the 13 districts. This is a "what-if" calculation inside the model, not a forecast. Because M2 is curved, the answer differs by district: drier districts sit on the steep part of the curve (`src/08_scenario_100mm.py`).

---

## 2. Repo map

"Feeds the report?" means the file's numbers or figures appear in `report/report.md`, directly or through `docs/REPORT_INPUTS.md`. **PROTOTYPE/HISTORICAL** marks files from the early stage that used subdivision rainfall and no temperature. They must not feed the report (`CLAUDE.md` rule 5; SPEC A11.5).

| Path | What it is | Created by | Used by | Feeds the report? |
|---|---|---|---|---|
| `CLAUDE.md` | project rules for the AI assistant (no editing raw data, no hand-typed numbers, logging) | team | all work | no |
| `config.py` | every path, seed, threshold, year range, district map, crosswalk and model setting | hand-written | every script | indirectly |
| `requirements.txt` | pinned Python packages | step 0 / A4 / A12 installs | setup | no |
| `run_all.sh` | runs the whole pipeline in order | hand-written (A14.6) | you | no |
| `README.md` | quick start | hand-written | you | no |
| `src/01`-`13`, `src/pipeline_utils.py` | the pipeline (Section 3) | hand-written | `run_all.sh` | yes (through outputs) |
| `data/raw/ICRISAT-District_Level_Data.csv` | crop area, production, yield | supplied | 01 | yes |
| `data/raw/rainfall_in_india_1901-2015.csv` | IMD monthly rainfall by subdivision | supplied | 02, 05b, 05c | validation only |
| `data/raw/district_wise_rainfall_normal.csv` | long-run district normals | supplied | 05b | validation only |
| `data/raw/era5_point_temperature.csv` | hourly temperature at one point | supplied | none (rejected, `docs/notes.md`) | no |
| `data/raw/grids/imd/` | 54 IMD .grd files + `manifest.json` (not in git or in the zip) | 05a | 05, 05c | yes (via panel) |
| `data/raw/boundaries/datameet_census2011/` | 2011 district shapefile | 05a | 05, 05b | yes (via panel) |
| `data/interim/district_subdivision_map.csv` | ICRISAT district -> IMD subdivision | 01 | 02, 05 | yes |
| `data/interim/subdivision_rainfall.csv` | subdivision Jun-Sep totals 2000-2015 | 02 | 05b, 05c | validation |
| `data/interim/old_to_current_districts.csv` | crosswalk 2011 district -> old ICRISAT district, with status and source | 05 | 05b, report Appendix B | yes |
| `data/interim/old_districts.gpkg` | dissolved old-district polygons | 05 | 05b | yes (maps) |
| `data/interim/grid_cell_weights.csv` | cell-district overlap areas | 05 | documentation | no |
| `data/interim/old_district_weather.csv` | weather for all 26 old districts x 18 years | 05 | 05b, 05c | validation |
| `data/interim/dq_flags.csv` | dq_flag check table | 05c | check only | no |
| `data/processed/soy_clean.csv`, `soy_clean_wide.csv` | cleaned crop data (13 / 17 districts) | 01 | 02, 05 | yes |
| `data/processed/panel_v1.csv`, `panel_v1_wide.csv` | **PROTOTYPE** panel, subdivision rainfall, 2000-2015 | 02 | 03 (prototype), 04 | no |
| `data/processed/panel_final.csv` | final panel, 234 rows | 05 | 03, 05b, 05c, 06-09, 11, 12 | yes |
| `data/processed/panel_final_wide.csv` | final panel, 17 districts (robustness) | 05 | 09 | yes (one row) |
| `outputs/tables/icrisat_*.csv` | step 01 audit and yield check | 01 | documentation | indirectly |
| `outputs/tables/prototype_*.csv`, `outputs/logs/prototype_models.txt` | **PROTOTYPE/HISTORICAL** step 04 | 04 | none | no |
| `outputs/tables/validation_*.csv`, `outputs/figures/validation_*.png`, `outputs/logs/05b_validation.txt` | panel validation | 05b | report 1.3, RESULTS_SUMMARY | yes |
| `outputs/prototype/` | **PROTOTYPE/HISTORICAL** 03 and 06-09 on panel_v1 (cannot be regenerated by the current 06-09) | old code | none | no |
| `outputs/final/tables/`, `figures/`, `logs/` | final results | 03, 05c, 06, 07, 08, 09, 11 | 10, 12, 13, report | yes |
| `docs/SPEC.md` | specification of record + amendments A1-A14 | hand-written | everyone | defines it |
| `docs/notes.md` | dated data decisions | hand-written | everyone | background |
| `docs/PROGRESS.md` | step-by-step log | hand-written | everyone | background |
| `docs/data_sources.md` | URLs, retrieval times, sizes, sha256 of downloaded files | 05a | report 1.3 | yes |
| `docs/data_dictionary.md` | column definitions of panel_v1 and panel_final | hand-written | report Appendix A | yes |
| `docs/HANDOFF.md` | status, issues, next steps | hand-written | team | background |
| `docs/RESULTS_SUMMARY.md` | every headline number with its source file | 10 | report authors | yes |
| `docs/REPORT_INPUTS.md` | report tables and figure list | 12 | report authors, 13 | yes |
| `docs/SUBMISSION_README.md` | one-page submission overview | hand-written | graders | no |
| `docs/literature/` | Lobell et al. 2011 PDF; teammate report (.docx) | supplied | report 1.2; crosswalk check | partly |
| `report/report.md` | the report | report authors | submission | it is the report |
| `report/figures_final/` | 21 copied figures + `MANIFEST.csv/.md` | 13 | report | yes |
| `dist/` | submission zip and file list | packaging step | submission | no |

---

## 3. Pipeline walkthrough

General pattern: each script reads from `data/` and writes to `data/` or `outputs/`. All constants come from `config.py`. Scripts 03, 06-09 and 11 take two arguments, `<panel.csv> <outdir>`, parsed by `pipeline_utils.parse_args`.

### 3.0 `src/pipeline_utils.py` (shared helpers, not a numbered step)

- **CLI and guard:** `parse_args`, `check_output_target`, `is_final`, `header` (see Section 7).
- **Output writer:** class `Outputs` writes CSVs with a `# header` first line (read them back with `pd.read_csv(..., comment="#")`), figures with a footer, and a text log.
- **Panel:** `load_panel` checks columns, duplicates, missing values and `ln_yield = log(yield_kgha)`. It then calls `centring_constants` and `add_model_columns`, which create `Rc = (R_season - mean)/100`, `Tc = T_season - mean`, the squares `Rc_sq` and `Tc_sq`, the centred timing variables `Rec` and `Rlc`, and `dry`.
- **Model catalogue:** the dictionary `MODELS` (M1, M2, M1_level, M2_level, timing, M2_rain_only). The key `rain` maps a regressor to "include its square?". It now holds temperature too; the name is left over from the rainfall-only stage.
- **Estimation:** `design` builds the regressors for a trend option (common, none, district, year_fe). `fit_fe` runs `linearmodels` PanelOLS with entity (district) effects and the covariance chosen from `COV_METHODS`. Class `FastFE` is a numpy version of the same estimator for bootstraps. It supports weights and year effects and is checked equal to PanelOLS.
- **Resampling:** `year_rows`, `block_draws`, `rows_from_year_draw`, `time_codes_from_year_draw`, `district_draws`, `rows_from_district_draw`.
- **Inference:** `wild_cluster_wald`, `boot_wald`, `boot_summary`.
- **Prediction and fit:** `lsdv_fit_predict` and `gaussian_ic`.
- **Scenarios:** `weather_lp` computes the weather part of the linear predictor from raw mm and deg C.
- **Legacy, currently unused:** `f_rain`, `effect`, `fe_params_fast`, `resample_years`, `resample_districts`, `wild_cluster_test`. A search of `src/` found no caller (this guide's check, 2026-10-20).

### 3.1 `src/01_clean_icrisat.py`

- **Purpose:** turn the ICRISAT file into clean soybean data and pick the districts.
- **Inputs:** `config.ICRISAT_FILE`.
- **Outputs:** `data/interim/district_subdivision_map.csv`; `data/processed/soy_clean.csv` (13 districts) and `soy_clean_wide.csv` (13 + 4); `outputs/tables/icrisat_audit.csv`; `icrisat_yield_check.csv`.
- **Main functions:** `write_district_map` (writes the map from `config.DISTRICT_SUBDIVISION`); `main` (rename by header, filter, checks, rule, audit).
- **Maths:** implied yield = 1000 x production (1000 t) / area (1000 ha), in kg/ha. District rule: keep district d if #{years with area >= `AREA_THRESHOLD` (20 thousand ha)} >= `MIN_YEARS` (15), counted over 2000-2017.
- **Checks:**
  - every expected header is present;
  - only Maharashtra rows, no missing values, no duplicate district-years;
  - every district is in the map;
  - zero area always comes with zero production and yield;
  - |reported - implied yield| <= `YIELD_CHECK_TOL` (1 kg/ha);
  - the wide-set extras exist and are not already selected.
- **Could fail if:** the ICRISAT headers change (the crop name is built from `config.CROP`), a district name is not in the map, or yield does not match production/area.

### 3.2 `src/02_build_panel_subdivision.py` (prototype panel; still needed for validation)

- **Purpose:** build the prototype panel with IMD *subdivision* rainfall (2000-2015), and the subdivision rainfall table used later for validation.
- **Inputs:** `soy_clean*.csv`, the IMD subdivision CSV, the district map.
- **Outputs:** `data/interim/subdivision_rainfall.csv`; `panel_v1.csv`, `panel_v1_wide.csv` (**PROTOTYPE**).
- **Functions:** `subdivision_rainfall` (sums monthly columns into R_season = JUN+JUL+AUG+SEP, R_early = JUN+JUL, R_late = AUG+SEP, R_julsep = JUL+AUG+SEP, and checks them against the file's own "Jun-Sep" column); `build` (joins via the map, adds `ln_yield` and `trend`, asserts rows = districts x years and no missing values); `main`.
- **Could fail if:** a subdivision string is misspelled. The file spells Marathwada "MATATHWADA", and the config copies that spelling.

### 3.3 `src/03_eda.py`

- **Purpose:** exploratory data analysis (EDA): summary statistics and descriptive figures.
- **Inputs:** a panel path.
- **Outputs:** `<outdir>/tables/eda_*.csv`, `<outdir>/figures/eda_*.png`.
- **Functions:** `save_table`, `save_fig`, `main`.
- **What it computes:** `describe()` statistics; mean yield by year; a district x year heatmap; a yield vs rainfall scatter; the subdivision rainfall series; a correlation matrix; an outlier table with within-district z = (x - mean_d)/sd_d, flagged when |z| > `OUTLIER_SD` (3). With district-level rainfall (the final panel) it averages districts within a subdivision and writes `eda_district_weather_context.csv`.
- **Checks:** the output guard (via `parse_args`), and subdivisions within the known set.
- **Could fail if:** the panel contains a subdivision outside `SUB_ORDER` (for example Konkan).

### 3.4 `src/04_models_prototype.py` (PROTOTYPE/HISTORICAL)

- **Purpose:** the first rainfall-only fixed-effects models on panel_v1.
- **Outputs:** `outputs/logs/prototype_models.txt`, `outputs/tables/prototype_*.csv`, each headed "PROTOTYPE - NOT FOR THE REPORT".
- **Functions:** `regressors`, `fit`, `rain_part`, `pct_change`, `experiments`, `main`; uses an iid year bootstrap with `config.SEED`.
- **Status:** not used by the report. It runs only with `run_all.sh --prototype`.

### 3.5 `src/05a_download_weather.py`

- **Purpose:** download the raw weather grids and the boundary file, and document them.
- **Outputs:** the shapefile parts in `data/raw/boundaries/datameet_census2011/`; `data/raw/grids/imd/archive/{rain,tmax,tmin}/<year>.grd` and `manifest.json`; `docs/data_sources.md`.
- **Functions:**
  - `download_boundaries` downloads from a URL pinned to `config.DATAMEET_COMMIT`, with two attempts per file, writing to a `.part` file first;
  - `maharashtra_bounds` reads the bounding box of the Maharashtra districts;
  - `download_imd` calls `imdlib.load(var, 2000, 2017, source="archive", cache_dir=...)` at most `DOWNLOAD_MAX_ATTEMPTS` (2) times per variable, and stops otherwise;
  - `check_grid` checks the grid extent covers Maharashtra and that every yearly file has its exact expected byte size;
  - `write_sources_doc` builds the source register from imdlib's manifest;
  - `sha256` checksums files.
- **Maths:** none. The file size is days x nlat x nlon x 4 bytes (float32), taken from `imdlib.util.GRIDS`.
- **Could fail if:** the IMD server is down. The script stops and does not substitute another source (SPEC A12.2); NASA POWER would be allowed for temperature only, with approval. It can also fail if GitHub is unreachable or the imdlib API changes.

### 3.6 `src/05_build_panel_gridded.py`

- **Purpose:** turn grids and polygons into one weather row per old ICRISAT district and year, then merge with yields into `panel_final.csv`.
- **Inputs:** the boundary shapefile, the imdlib cache, `soy_clean*.csv`, the district map.
- **Outputs:** `old_to_current_districts.csv`, `old_districts.gpkg`, `grid_cell_weights.csv`, `old_district_weather.csv`, `panel_final.csv` (13 x 18), `panel_final_wide.csv` (17 x 18).
- **Main functions:**
  - `canonical` normalises a name and applies `config.SPELLING_VARIANTS` (approved variants only);
  - `load_current_districts` reads the 35 Maharashtra polygons and stops on any unmatched name;
  - `crosswalk_table` and `check_crosswalk` implement the crosswalk guard (Section 7);
  - `alias_sanity_check` handles renamed districts (not applicable to the 2011 layer);
  - `build_crosswalk_and_dissolve` writes the crosswalk CSV and dissolves (merges) current polygons into old districts;
  - `cell_weights` computes overlap areas;
  - `daily_district_means` gives each district's daily weighted mean;
  - `longest_run`, `season_slice` and `dq_flag` build the derived variables.
- **Maths:**
  - Overlap weight of cell c in district d: w_dc = area(cell_c intersected with polygon_d), in the equal-area projection `ESRI:102028`.
  - Daily district value: x_d(day) = sum_c w_dc x_c(day) / sum_c w_dc over cells with valid data. If none is valid, the nearest valid cell is used and counted.
  - R_season = sum over 1 Jun-30 Sep of the daily rainfall (mm); R_early covers 1 Jun-31 Jul, R_late 1 Aug-30 Sep, R_julsep 1 Jul-30 Sep.
  - dry_spell_max = the longest run of consecutive days with district rain < `DRY_DAY_MM` (2.5 mm).
  - T_season = the mean over the season of (Tmax + Tmin)/2.
  - dq_flag = 1 if |R_season - district median| > 3 x 1.4826 x MAD. MAD is the median absolute deviation; 1.4826 x MAD is the "robust SD".
- **Checks:**
  - exactly 35 Maharashtra districts with valid geometries, every name matched, no duplicates;
  - every old district has polygons, and dissolved areas equal the sum of member areas;
  - overlap areas sum to each district's area;
  - the season has 122 days, R_early + R_late = R_season, and every daily value is finite;
  - the panels have 13 x 18 and 17 x 18 rows, unique keys and no missing values.
- **Could fail if:** a boundary name has no approved variant (the script stops; this happened with 6 names, which the user then approved, `docs/notes.md`). It also fails if an UNVERIFIED crosswalk pair is used, or if the grids are missing (imdlib `offline=True` raises).

### 3.7 `src/05b_validate_panel.py`

- **Purpose:** check the gridded panel against independent sources before any model is fitted.
- **Outputs:** `outputs/tables/validation_*.csv`, `outputs/figures/validation_*.png`, `outputs/logs/05b_validation.txt`.
- **Functions:** class `Out` (writer), `main`. It loads `05_build_panel_gridded.py` with `importlib` to reuse `canonical`.
- **What it computes:**
  - (a) correlation and mean ratio of gridded vs IMD subdivision rainfall for 2000-2015, with each subdivision rebuilt as an area-weighted mean of its old districts;
  - (b) the ratio of gridded mean R_season to the area-weighted district normals, flagged if |ratio - 1| > `VALIDATION_NORMAL_TOL` (0.25);
  - (c) plausibility: temperature ordering, Tmax > Tmin, missing cells, maps and bars;
  - (d) the correlation of R and T, pooled and within district; VIF; the cross-district rainfall correlation matrix and its eigenvalues, the participation ratio, and the number of components for 90% of the variance;
  - (e) yield vs rainfall and yield by year.
- **Could fail if:** a normals-file name does not match (it stops), or 05 has not been run.

### 3.8 `src/05c_diagnose_ghats.py`

- **Purpose:** diagnose suspicious rainfall values by reading the raw bytes (SPEC A13.4a).
- **Outputs:** `outputs/final/tables/05c_*.csv`, `outputs/final/logs/05c_diagnose_ghats.txt`, `data/interim/dq_flags.csv`.
- **Functions:**
  - `raw_rain` reads a .grd file with `np.fromfile(..., "<f4")` and reshapes it to (day, lat, lon);
  - `robust_z` computes z = (R - median_d)/(1.4826 MAD_d);
  - `main` builds the case table, the imdlib masking check, the sentinel scan and the verdict.
- **Checks:** that imdlib's NaNs are exactly the -999 cells, that unmasked values are identical to the raw bytes, and that the panel's `dq_flag` equals the 05c screen.
- **Result:** no processing bug; the anomalies are properties of the IMD product (`docs/notes.md`, 2026-10-19).

### 3.9 `src/06_models_final.py`

- **Purpose:** estimate the final models, compare linear vs quadratic, and apply the headline rule.
- **Outputs:** `06_models_{centring_constants, coefficients, se_comparison, fit_stats, linear_vs_quadratic, loyo_by_year, trend}.csv` and the log `06_models.txt`.
- **Functions:** `loyo` (leave one year out), `mbb` (moving-block bootstrap of the coefficients), `main`.
- **Equations** (d = district, t = year; Rc in units of 100 mm; Tc in deg C):
  - M1: ln Y_dt = alpha_d + gamma t + b1 Rc_dt + b2 Tc_dt + e_dt
  - M2: ln Y_dt = alpha_d + gamma t + b1 Rc_dt + b3 Rc_dt^2 + b2 Tc_dt + b4 Tc_dt^2 + e_dt
- **Verdict:** joint Wald test of b3 = b4 = 0 under district-CR, wild bootstrap, year-CR, two-way CR, Driscoll-Kraay and MBB L = 3. All significant at `ALPHA` (0.05) gives QUADRATIC SUPPORTED; none significant gives LINEAR ADEQUATE; anything else is INCONCLUSIVE. The headline rule (A11.1) is coded right after the verdict.
- **Fit:** within R-squared; AIC = -2 llf + 2k and BIC = -2 llf + k ln n, with llf = -n/2 [ln(2 pi) + ln(SSR/n) + 1] (`gaussian_ic`); a classical F test (reported, not in the verdict); turning points.
- **Trend check:** M1, M2 and trend-only fitted on 2000-2017 and on 2000-2015.
- **Could fail if:** the panel has no `T_season` (for example panel_v1). `load_panel` then asserts with a clear message.

### 3.10 `src/07_diagnostics.py`

- **Purpose:** check the residuals of M1 and M2 and their stability.
- **Outputs:** `07_diag_{tests, influence, leave_one_district_out, collinearity}.csv` and five figures.
- **Functions:**
  - `lsdv` refits each model as ordinary least squares with district dummies (LSDV), using `statsmodels`, so residual tools apply, and asserts the slopes equal PanelOLS;
  - `wooldridge_ar1` implements the serial-correlation test;
  - `pesaran_cd` implements the cross-sectional dependence test;
  - `main` also runs Breusch-Pagan, Brown-Forsythe (Levene with median centring), Jarque-Bera, influence measures (leverage, studentized residuals, Cook's distance, DFBETAS), leave-one-district-out refits and R-T collinearity (VIF, condition number).
- **Equations:** see the glossary.

### 3.11 `src/08_scenario_100mm.py`

- **Purpose:** the numerical experiments.
- **Inputs:** the panel, plus `06_models_linear_vs_quadratic.csv` (the headline model is read from it).
- **Outputs:** `08_scenario_{results, range_curve, district_means}.csv` and two figures.
- **Functions:** `slopes` (within-district OLS slope of T on R for each district), `scenario_effects`, `range_curve`, `main`.
- **Maths:**
  - For district d: Delta_d = f(R_new, T_new) - f(Rbar_d, Tbar_d), where f is `pipeline_utils.weather_lp`. The percent change is exp(Delta_d) - 1, and kg/ha = pct x Ybar_d (the district's mean observed yield).
  - Variant A (headline): T_new = Tbar_d. Variant B: T_new = Tbar_d + s_d (R_new - Rbar_d).
  - Scenarios: deficit_100mm, surplus_100mm, weak_monsoon_90pct and _80pct; exploratory timing split and M2_rain_only.
  - Subdivision and state rows are unweighted means of the district rows. Intervals are percentile intervals from the MBB (L = 2, 3, 4) and a district bootstrap. s_d is re-estimated in every replication.
- **Checks:** R_early + R_late = R_season in the district means, FastFE = PanelOLS, and the 06 table exists.

### 3.12 `src/09_robustness.py`

- **Purpose:** test whether the 100 mm result survives different choices.
- **Outputs:** `09_robust_results.csv` (with `interval_method`), `09_robust_variance_share.csv`, four area-weighting tables and two figures.
- **Functions:**
  - `effect_mean` gives the mean over districts of exp(Delta_d) - 1, with a delta-method interval from the year-clustered covariance;
  - `mbb_effect` gives the moving-block bootstrap distribution of the same quantity (for year_fe, drop_kolhapur_sangli and area_weighted; A14.3);
  - `variance_share` gives the share of district-demeaned R and T explained by year dummies;
  - `area_weighting_investigation` covers weight shares, the Kish effective number = 1 / sum(share^2), the between/within decomposition, district-specific slopes and weighted leave-one-district-out;
  - `pct100` and `main`.
- **Variants:** listed in `main`; see report Table 9.

### 3.13 `src/10_results_summary.py`

- **Purpose:** write `docs/RESULTS_SUMMARY.md` purely from output tables, so that no number is typed by hand.
- **Functions:** `rd` reads a table and returns its path; `pc` formats percentages; `main`.
- **Could fail if:** a table is missing; it asserts and names the script to run.

### 3.14 `src/11_sanity_checks.py`

- **Purpose:** independent checks (A14.5).
- **Function `lp`:** an independent re-implementation of the weather predictor, used to recompute the headline from the stored coefficient CSV.
- **What `main` writes:** turning points with the share of observations on each side; response curves for the driest, median and wettest district, with an MBB band; surplus-vs-deficit symmetry.
- **Checks:** the recomputation equals 08 within 1e-9 (percent) and 1e-6 (kg/ha); otherwise the script exits with FAIL.

### 3.15 `src/12_report_inputs.py`

- **Purpose:** write `docs/REPORT_INPUTS.md`: tables and the figure list with captions and report subsections.
- **Functions:** `rd`, `md` (markdown table writer), `pct`, `main`. The list `FIGURES` holds (path, caption, subsection).
- **Checks:** every listed figure exists, and every PNG in `outputs/final/figures` is listed.

### 3.16 `src/13_collect_report_figures.py`

- **Purpose:** copy the listed figures into `report/figures_final/` and write `MANIFEST.csv/.md`.
- **Functions:** `figure_table` parses the "Figure list" table of `REPORT_INPUTS.md`; `main` copies the files, checks each sha256 against its source, and asserts unique names and that every file exists.

### 3.17 `run_all.sh`

- **What it runs:** 01, 02, (03 and 04 only with `--prototype`), 05a (skipped with `--skip-download`, which first checks 54 grids and the shapefile exist), 05, 05c, 05b, then 03, 06, 07, 08, 09 and 11 on `panel_final.csv` into `outputs/final`, then 10, 12, 13.
- **Behaviour:** `set -euo pipefail` stops at the first error.
- **Test:** reproducibility was tested on 2026-10-19 (`docs/PROGRESS.md`, A14 entry). After deleting `data/processed` and `outputs/final`, all 60 CSV tables, all 21 PNG figures and both generated docs (excluding the timestamp line) were byte-identical. The run took about 28 s.

---

## 4. Data lineage

```
data/raw/ICRISAT-District_Level_Data.csv --01--> data/processed/soy_clean.csv --+
data/raw/rainfall_in_india_1901-2015.csv --02--> data/interim/subdivision_rainfall.csv --(validation 05b, 05c)
(IMD server via imdlib) --05a--> data/raw/grids/imd/*.grd ----------------------+
(DataMeet GitHub) --05a--> data/raw/boundaries/.../2011_Dist.shp ---------------+
                                                                                v
        05: crosswalk + dissolve + overlap weights + daily means --> data/interim/old_*.{csv,gpkg}
                                                                --> data/processed/panel_final.csv (+ _wide)
panel_final.csv --05b/05c--> validation + diagnosis tables
panel_final.csv --03, 06, 07, 08, 09, 11--> outputs/final/{tables,figures}
outputs/final/tables --10--> docs/RESULTS_SUMMARY.md ;  --12--> docs/REPORT_INPUTS.md --13--> report/figures_final/
report/report.md cites report/figures_final/ and the numbers in the tables above
```

### Report element -> script -> file

The mapping is based on matching the report's text and numbers with the output tables (this guide's check). The report itself no longer carries per-subsection source comments.

| report/report.md element | Produced by | File |
|---|---|---|
| Summary numbers | 08, 09 | `08_scenario_results.csv`, `09_robust_results.csv` |
| 1.3 data counts (464 rows, 68 zero-area rows) | 01 | `docs/notes.md` (01 entry), `outputs/tables/icrisat_audit.csv` |
| Table 1 (districts) | 12 (from the panel) | `docs/REPORT_INPUTS.md` Table 1 <- `data/processed/panel_final.csv` |
| 1.3 cell counts (rain 17-57, temperature 2-8, 7 districts without a centre) | 05 | `docs/notes.md`, `data/interim/grid_cell_weights.csv` |
| 1.3 validation correlations and ratios, Kolhapur normal | 05b | `outputs/tables/validation_a_subdivision_comparison.csv`, `validation_b_normals_comparison.csv` |
| Figures 1-3 | 05b | `validation_a_subdivision_series.png`, `validation_c_map_rainfall.png`, `validation_c_map_temperature.png` |
| 1.3 data-quality paragraph | 05c | `outputs/final/tables/05c_cases.csv`, `05c_robust_z_panel.csv` |
| 1.3 participation ratio, mean correlation | 05b | `outputs/tables/validation_d_summary.csv` |
| 1.4 grand means | 06 | `06_models_centring_constants.csv` |
| Table 2 | 03 | `outputs/final/tables/eda_summary_stats.csv` |
| Figures 4-8 | 03 | `eda_mean_yield_by_year.png`, `eda_yield_heatmap.png`, `eda_yield_vs_rseason.png`, `eda_rainfall_by_subdivision.png`, `eda_correlation_matrix.png` |
| 1.4 collinearity sentence | 05b, 07 | `validation_d_summary.csv`, `07_diag_collinearity.csv` |
| Table 3 | 06 | `06_models_se_comparison.csv` |
| 2.3 turning points, shares | 06, 11 | `06_models_fit_stats.csv`, `11_sanity_turning_points.csv` |
| Table 4a | 06 | `06_models_linear_vs_quadratic.csv` |
| Table 4b | 06 | `06_models_fit_stats.csv` |
| Tables 5, 6, 7; 3.1-3.2 text | 08 | `08_scenario_results.csv` |
| 3.1 "within-district SD 188 mm" | 11 | `11_sanity_turning_points.csv` |
| 3.3 asymmetry | 11 | `11_sanity_symmetry.csv` |
| Figures 9-10 | 08 | `08_scenario_district_effects.png`, `08_scenario_range_curve.png` |
| Figure 11 | 11 | `11_sanity_response_curves.png` |
| 3.3 arithmetic check | 11 | `11_sanity_headline_recompute.csv` |
| Table 8, 4.1 text | 07 | `07_diag_tests.csv`, `07_diag_collinearity.csv` |
| Figures 12-16 | 07 | `07_diag_resid_vs_fitted.png`, `07_diag_qq.png`, `07_diag_resid_by_year.png`, `07_diag_resid_by_district.png`, `07_diag_leave_one_district_out.png` |
| 4.2 numbers | 07, 09 | `07_diag_leave_one_district_out.csv`, `09_robust_results.csv` |
| Table 9, 4.3 text | 09 | `09_robust_results.csv`, `09_robust_variance_share.csv`, `09_robust_weighting_decomposition.csv`; trend from `06_models_trend.csv` |
| Figure 17 | 09 | `09_robust_forest.png` |
| Appendix A | hand-written | `docs/data_dictionary.md`, SPEC A12.5/A13.4 |
| Appendix B | 05 (statuses); split dates from the teammate report | `data/interim/old_to_current_districts.csv`; dates from `docs/literature/teammate_report.docx` (Table 4) and the team lead (Washim), not from code |
| Appendix C | run_all test | `docs/PROGRESS.md` (A14 entry) |

Figures collected but **not used** in report.md: `validation_c_bars.png`, `validation_d_rainfall_correlation.png`, `validation_e_yield.png`, `09_robust_area_weighting.png` (this guide's comparison of report.md with `report/figures_final/`).

---

## 5. Glossary

Each entry gives a plain explanation, why it was used, and where it lives in the code.

- **Fixed effects (FE).** A separate intercept for each district (alpha_d) or each year. District FE remove everything constant about a district. *Why:* districts differ permanently (Kolhapur's mean yield is about twice Nagpur's, `docs/REPORT_INPUTS.md` Table 1), and we must not credit that to weather. *Code:* `entity_effects=True` in `pipeline_utils.fit_fe`. Year FE (`time_effects=True`, trend option "year_fe") are a robustness variant.
- **Within estimator.** The way FE models are computed: subtract each district's own mean from y and x ("demeaning"), then run ordinary least squares on the demeaned data. It gives the same slopes as adding a dummy per district. *Code:* PanelOLS; `FastFE.fit` (demeaning with `np.bincount`); `07_diagnostics.lsdv` (the dummy version).
- **Centring.** Subtract the panel mean before squaring: Rc = (R - Rbar)/100, Tc = T - Tbar. In M2 the linear coefficient is then the slope at the average weather, and the linear and squared terms are less correlated. *Code:* `centring_constants`, `add_model_columns`. The constants are in `06_models_centring_constants.csv` (R_season 810.387922 mm, T_season 27.447367 deg C).
- **Quadratic turning point.** For y = b1 x + b3 x^2, the slope is zero at x* = -b1/(2 b3): a maximum if b3 < 0, a minimum if b3 > 0. In raw units R* = Rbar + 100 x (-b1/(2 b3)). *Code:* `06_models_final.main` (`turning_point_*`) and `11_sanity_checks.main`. Values: 1239.96 mm and 26.93 deg C (`11_sanity_turning_points.csv`).
- **Clustered standard errors.** A *standard error* (SE) measures how uncertain a coefficient is. Classical SEs assume every observation's error is independent. A *cluster* is a group whose errors may be correlated (all districts in one year, or all years of one district). Cluster-robust (CR) SEs allow any correlation inside a cluster. *Why:* districts share weather shocks and districts persist over time. *Code:* `COV_METHODS` "year_CR" and "district_CR" in `pipeline_utils.py`.
- **Two-way clustering.** Allows correlation within districts *and* within years at the same time. *Code:* `COV_METHODS["twoway_CR"]`.
- **Driscoll-Kraay (DK).** SEs that allow correlation across all districts in a year and over a few lags of years, using a Bartlett kernel (weights 1, 2/3, 1/3 for lags 0, 1, 2). *Why:* the same dependence as the data shows. It needs many years, so it is flagged unreliable with 18. *Code:* `COV_METHODS["driscoll_kraay"]` with `bandwidth=config.DK_MAXLAGS` (2). The lag weights were checked against linearmodels' source (`docs/notes.md`, A7 implementation).
- **Wild cluster bootstrap.** A resampling test that works with few clusters. Fit the model with the tested coefficients set to zero ("restricted"). Then build new outcomes by flipping the sign of each district's residuals at random (Rademacher weights, +1 or -1), refit, and count how often the new test statistic exceeds the original. With 13 districts there are 2^13 = 8192 sign patterns, so all are enumerated and the p-value is exact. *Code:* `pipeline_utils.wild_cluster_wald` (joint Wald; for one coefficient it equals the bootstrap-t).
- **Moving-block bootstrap (MBB).** Resample whole years in *blocks of consecutive years* (length L = 3), keeping all 13 districts of a year together, and refit the full model each time. The spread of the refitted results gives the interval. Blocks keep short-run dependence across years, and whole years keep dependence across districts. *Code:* `block_draws`, `rows_from_year_draw`, `FastFE`, `06.mbb`, `08.main`, `09.mbb_effect`. Settings: `N_BOOT_BLOCK` = 2000, `BOOT_SEEDS` (L2 2802, L3 2803, L4 2804, districts 2810, wild 2820) in `config.py`. Intervals are percentile intervals (2.5th and 97.5th percentiles). The p-value is 2 x min(share <= 0, share >= 0) (`boot_summary`). The joint test uses W = theta' Cov_boot^-1 theta (`boot_wald`).
- **Duan smearing.** If the model predicts ln Y, then exp(prediction) estimates the *median* of Y, not the mean, so it is biased low. Duan's correction multiplies by the average of exp(residuals) from the fitting sample. *Code:* `06_models_final.loyo` (`smear_factor`). Both naive and smeared errors are reported (A9).
- **Leave-one-year-out (LOYO) prediction.** For each year, fit the model on the other years, predict the left-out year, and measure the error (RMSE = root mean squared error). It shows whether the model predicts new years, not just fits old ones. *Code:* `06_models_final.loyo`, `pipeline_utils.lsdv_fit_predict`.
- **Breusch-Pagan (BP).** Tests whether the residual variance depends on the regressors (heteroskedasticity) by regressing squared residuals on them: LM = n R^2. *Code:* `statsmodels het_breuschpagan` in `07_diagnostics.main`.
- **Brown-Forsythe.** Tests whether the residual spread differs across groups (districts or years). It is Levene's test using group medians. *Code:* `scipy.stats.levene(center="median")`.
- **Jarque-Bera (JB).** Tests whether residuals look normal, using skewness S and kurtosis K: JB = n/6 (S^2 + (K-3)^2/4). *Code:* `statsmodels jarque_bera`.
- **Wooldridge serial-correlation test.** Tests whether a district's error is correlated with its previous year's error. Take first differences of the model, get the residuals u, regress u_t on u_{t-1}. With no serial correlation the coefficient should be -0.5, so test that with district-clustered SEs: F = ((b + 0.5)/se)^2. *Code:* `07_diagnostics.wooldridge_ar1`.
- **Pesaran CD test.** Tests whether residuals of different districts move together within a year: CD = sqrt(2T/(N(N-1))) x sum over pairs of the correlation rho_ij, approximately standard normal if there is no dependence. *Code:* `07_diagnostics.pesaran_cd`.
- **VIF (variance inflation factor).** For each regressor, regress it on the others; VIF = 1/(1 - R^2). Large values (for example above 10) mean collinearity inflates the SEs. *Code:* `05b_validate_panel.main` (part d), `07_diagnostics.main` (collinearity table), both on district-demeaned data.
- **Participation ratio.** Take the correlation matrix of the 13 districts' rainfall series and its eigenvalues lambda_i. PR = (sum lambda_i)^2 / sum lambda_i^2. It equals 13 if all series were independent and 1 if they were identical, so it reads as the "effective number of independent rainfall signals". The value is 2.56 (`outputs/tables/validation_d_summary.csv`). *Code:* `05b_validate_panel.main` (part d).
- **Delta method.** A way to get the SE of a function g(beta) of coefficients: Var(g) is approximately grad(g)' V grad(g), where V is the coefficients' covariance matrix. Used for the robustness intervals of the mean percent effect, whose gradient is mean_d exp(Delta_d) x dDelta_d/dbeta. *Code:* `09_robustness.effect_mean`.

---

## 6. Decision log in plain language

The source for every entry is `docs/SPEC.md` (amendments) and `docs/notes.md`.

| Amendment | What was decided | Why | What it changed |
|---|---|---|---|
| (initial SPEC, 2026-10-18) | Soybean, 2000-2017 target, district rule, ln(yield), rainfall-only linear/quadratic, year-clustered SEs "as a stopgap" | first plan with subdivision rainfall | 01-04 prototype |
| A1 | District set defined once from 2000-2017 (13 districts) | the set should describe where soybean is grown, not depend on rainfall coverage | 01 rule window |
| A2 | Keep the six small-area district-years; robustness: drop them, and area weights | early-expansion years are real data | 09 variants drop_small_area, area_weighted |
| A3 | Timing model: split 100 mm by each window's share; quadratic timing is exploratory | define the timing scenario before results | 08 timing rows |
| A4 | Install xarray, netCDF4, geopandas, shapely | needed for grids and polygons | requirements.txt |
| A5 | Fixed 13 districts; robustness with 4 more; crosswalk pairs UNVERIFIED until confirmed | robustness to the borderline districts | `soy_clean_wide`, `panel_*_wide`, 09 wider_districts |
| A6 | Primary common linear trend; robustness: none, district trends, year FE (only with district-level rainfall) | locked before the gridded results | 09 trend variants |
| A7 | Headline intervals from the MBB over years (L = 3; 2 and 4 as sensitivity; 2000 reps); report six inference methods; the verdict must agree across methods | the prototype diagnostics showed serial and cross-sectional dependence | pipeline_utils inference helpers; 06, 08 |
| A8 | Report structure (professor's format) | required format | `report/report.md` headings |
| A9 | Percent is the headline unit; kg/ha baseline = district mean yield; Duan smearing; investigate area weighting; re-examine the trend | consistency and transparency | 06 loyo, 08 kg/ha, 09 investigation |
| A10 | Crosswalk statuses (CONFIRMED_OFFICIAL_PAGE, CAVEAT, UNVERIFIED); guard blocks only used UNVERIFIED pairs; robustness dropping Akola, Parbhani, Osmanabad, Chandrapur | boundary uncertainty | `config.DISTRICT_CROSSWALK`, `check_crosswalk`, 09 drop_boundary_sensitive |
| A11 | Verdict scope confirmed; **pre-specified headline rule** (inconclusive -> linear headline); renames are aliases; Partur kept in Aurangabad (limitation); Washim confirmed; outputs/prototype is historical | avoid choosing the model after seeing results | 06 headline code; crosswalk statuses |
| A12 | Acquire weather ourselves via imdlib + DataMeet; fractional-overlap aggregation; variable definitions (incl. dry_spell_max, T_season); validation before models | the teammate did not deliver data | 05a, 05, 05b; panel_final |
| A13 (the team lead called it "A12") | Headline models now include temperature (M1, M2, centred); variants A/B; data-quality diagnosis and dq_flag rule; robustness list; trend re-examination | written before the final model run | 05c; 06-09 rewritten |
| A14 | Year FE is a prominent stability result with a variance-share analysis; dq_flag kept as applied; MBB for three robustness rows; sanity checks; run_all.sh + reproducibility test; REPORT_INPUTS | transparency and reproducibility | 09 variance share and MBB rows; 11, 12, run_all.sh; 08 surplus rows |

Two further decisions were approved by the user rather than the team lead (`docs/notes.md`, 2026-10-19). Six DataMeet spellings were accepted (Bid, Buldana, Garhchiroli, Gondiya, Raigarh, Mumbai), and Sindhudurg was mapped to Ratnagiri as UNVERIFIED.

---

## 7. Guards and safety checks

| Guard | Where | What it does | Protects against |
|---|---|---|---|
| outputs/final guard | `pipeline_utils.check_output_target` (called by `parse_args`) in 03, 06-09, 11 | refuses (exits) if the output folder is under `outputs/final` and the input is not exactly `config.PANEL_FINAL_FILE` (resolved path, not just the name); the same for the wide panel | prototype or test results leaking into the report folder |
| Output header | `pipeline_utils.header`, `Outputs` | every table and figure says PROTOTYPE or FINAL | confusing prototype with final results |
| Crosswalk guard | `05_build_panel_gridded.check_crosswalk` | stops if a current district is unmapped, a panel district has no polygon, or a used pair is UNVERIFIED; ALIAS_NAME_ONLY and CAVEAT never block | wrong or unconfirmed boundary merges |
| Name matching stop | `load_current_districts` | stops on any spelling outside `config.SPELLING_VARIANTS` | silent name guessing |
| Download failure stop | `05a.download_imd`, `download_boundaries` | stops after two failed attempts; no substitute source | silently using unapproved data |
| Panel asserts | 02 `build`, 05 `main`, `pipeline_utils.load_panel` | rows = districts x years, unique keys, no missing values, ln_yield = log(yield) | broken merges, missing data |
| Estimator equality | 07 (LSDV = PanelOLS), 08 and 11 (FastFE = PanelOLS), A14 check on resampled panels (`docs/notes.md`) | the fast bootstrap estimator gives the same numbers as the reference library | bugs in the bootstrap code |
| Independent recomputation | `11_sanity_checks` | recomputes the headline from stored coefficients; exits with FAIL on mismatch | errors in scenario code |
| dq_flag consistency | `05c` vs `05.dq_flag` | asserts the same rule gives the same flags | two definitions drifting apart |
| Figure list completeness | 12, 13 | every figure exists and is listed | missing or orphaned report figures |
| Yield and unit checks | 01 | implied vs reported yield within 1 kg/ha; zero-area consistency | unit mistakes |

---

## 8. How to reproduce, and how to change something

**Reproduce:** follow `README.md`. In short: create the venv, `pip install -r requirements.txt`, then `bash run_all.sh` (the first run downloads about 500 MB, `README.md`) or `bash run_all.sh --skip-download`.

**How to change something (files to edit):**

| Change | Edit | Notes |
|---|---|---|
| Different crop (e.g. cotton) | `config.CROP` (the header prefix, e.g. "COTTON"), `EXPECTED_DISTRICTS`, `ROBUST_EXTRA_DISTRICTS` | 01 builds column names from `CROP`. 05's `main` hard-codes the expected district counts 13 and 17 in its panel loop, so edit those too. Report text and some log strings say "13 districts" (e.g. 12 Table 1 title, 08 headline log). SPEC says cotton is out of scope (A13.4d). Untested: **not verified**. |
| Different period | `YEAR_START`, `YEAR_END_TARGET`, `WEATHER_YEAR_START/END`, `TREND_BASE_YEAR` in `config.py` | 05a downloads the new years; the 18-year assumptions in panel asserts follow config. **Not verified** for other periods. |
| District rule | `AREA_THRESHOLD`, `MIN_YEARS` in `config.py`; update the hard-coded 13/17 in `05_build_panel_gridded.main` | the crosswalk guard will check the new districts |
| Model terms | `MODELS` in `pipeline_utils.py`; `FITTED`/`PAIRS` in `06_models_final.py`; `PAIR` in `08`; `FORMS` in `09` | the scenario code uses `weather_lp`, which knows Rc, Tc, Rec, Rlc, dry |
| Scenarios | `RAIN_SHOCK_MM`, `WEAK_MONSOON_FRACTIONS` in config; `scenario_effects` in 08 | |
| Inference settings | `BLOCK_LENGTH`, `BLOCK_LENGTH_SENSITIVITY`, `N_BOOT_BLOCK`, `BOOT_SEEDS`, `DK_MAXLAGS`, `ALPHA` in config | changing them changes numbers; record a SPEC amendment |
| Robustness variants | list `V` in `09_robustness.main`; `MBB_VARIANTS` | |
| Crosswalk | `DISTRICT_CROSSWALK`, `SPELLING_VARIANTS`, `CROSSWALK_SOURCE_OVERRIDES` in config | |

Project rules: any SPEC change needs approval and a dated amendment, and decisions are logged in notes.md and PROGRESS.md (`CLAUDE.md`).

---

## 9. Known problems and limitations

**Data**
1. Only 18 years, and rainfall is largely shared: the participation ratio is 2.56 (`validation_d_summary.csv`). Intervals are therefore wide and depend on the inference method.
2. With year fixed effects the effect shrinks to -3.20% [-8.39%, +0.64%] (M2) and +2.09% (M1) (`09_robust_results.csv`). The headline reflects state-wide monsoon variation and cannot be separated from other state-wide shocks.
3. The gridded IMD rainfall shows artefacts in the Western Ghats: Ratnagiri and Raigad 2008 at a ratio of 0.54, Pune 2005 at 1.27 (`05c_cases.csv`). Kolhapur's gridded mean is 0.63 of its normal (`validation_b_normals_comparison.csv`).
4. Temperature comes from a 1-degree grid. Districts overlap only 2-8 cells and 7 old districts contain no cell centre (`docs/notes.md`), so T_season varies little and is measured coarsely.
5. The dq_flag rule flagged Buldhana wet years, not the Ghats (A14.2).

**Boundaries and variables**
6. Boundaries: Partur taluka is kept in Aurangabad (A11.3). Crosswalk pairs other than Washim rest on the teammate's citations and are not independently verified (`config.DISTRICT_CROSSWALK` notes).
7. There are no irrigation, input, price, pest or sowing-date controls. M2's within R-squared is 0.288 (`docs/RESULTS_SUMMARY.md`).

**Diagnostics and fit**
8. Residuals are heteroskedastic, serially correlated and cross-sectionally dependent, and not normal (`07_diag_tests.csv`). The model leaves common year shocks unexplained.
9. The trend is negative and not significant, and is not interpreted (`06_models_trend.csv`).
10. The rainfall turning point (1239.96 mm) has only 0.060 of observations above it (`11_sanity_turning_points.csv`). The data say little about losses from excess rain.

**Code**
11. Unused legacy helpers remain in `pipeline_utils.py` (Section 3.0). The `MODELS` key `rain` now also holds temperature terms.
12. 05 hard-codes the panel sizes 13 and 17.
13. `outputs/prototype` cannot be regenerated with the current 06-09, which need temperature. It is a historical record only.
14. 04 still uses an iid year bootstrap (prototype only).
15. 05a depends on IMD's server and the imdlib API (0.3.1). Future availability is **not verified**.

---

## 10. Twenty questions a professor might ask

1. **What exactly is your outcome and why log?** ln(yield in kg/ha). Coefficients then read as approximate percent changes, and multiplicative effects are natural for yields. (`src/pipeline_utils.py` `load_panel`; `docs/SPEC.md`.)
2. **What do district fixed effects remove, and what do they not remove?** Anything constant within a district. They do not remove shocks that change over time, such as prices, pests or policy. (`report/report.md` 1.6; `CLAUDE.md` rule 4.)
3. **Why centre the variables?** So that M2's linear coefficients are slopes at the average weather, and the squares are less collinear with the linear terms. (`add_model_columns`; `06_models_centring_constants.csv`.)
4. **How did you choose between linear and quadratic?** By a rule fixed in advance: the joint test of both squares must be significant under all six methods. Every method gave p <= 0.0020, so QUADRATIC SUPPORTED. (`06_models_linear_vs_quadratic.csv`; SPEC A11.1.)
5. **What is the headline and its interval?** -10.04% [-15.18%, -4.29%], or -117.2 kg/ha [-176.6, -50.7]. (`08_scenario_results.csv` via `docs/RESULTS_SUMMARY.md`.)
6. **Why a moving-block bootstrap?** Residuals are correlated across districts within a year (Pesaran CD 12.543) and within districts over time (Wooldridge p 0.0019). Resampling blocks of whole years keeps both kinds of dependence. (`07_diag_tests.csv`; `pipeline_utils.block_draws`.)
7. **Why is the effect different for each district in M2?** One pooled curve, with districts at different mean rainfall: Sangli -17.30%, Chandrapur -0.96%. It is not a separate estimate per district. (`08_scenario_results.csv`.)
8. **What happens with year fixed effects and why?** The M2 effect falls to -3.20% [-8.39%, +0.64%], because year dummies explain 0.562 of the within-district rainfall variance. (`09_robust_results.csv`, `09_robust_variance_share.csv`.)
9. **Is this causal?** No. These are associations: state-wide shocks move with the monsoon, and there are no irrigation or input controls. (`report/report.md` 1.6; `CLAUDE.md`.)
10. **How were district weather values built?** Area-weighted means over grid cells, with weights equal to the overlap area in an equal-area projection; daily means first, then seasonal sums or means. (`05_build_panel_gridded.cell_weights`, `daily_district_means`.)
11. **How did you handle old vs new district boundaries?** Each old ICRISAT district is dissolved from its 2011 successors via a status-checked crosswalk, and a guard blocks unverified pairs. (`config.DISTRICT_CROSSWALK`, `check_crosswalk`, `old_to_current_districts.csv`.)
12. **How do you know the gridded data are right?** Gridded rainfall correlates with IMD subdivision totals at 0.972 (Vidarbha), 0.964 (Marathwada) and 0.884 (Madhya Maharashtra). A raw-byte diagnosis found no sentinel or processing errors. (`validation_a_subdivision_comparison.csv`, `05c_imdlib_masking.csv`, `05c_sentinel_scan.csv`.)
13. **What is the "effective number of independent rainfall signals"?** The participation ratio of the rainfall correlation eigenvalues: 2.56. (`validation_d_summary.csv`; `05b_validate_panel.main`.)
14. **Does the model predict better than a trend alone?** Modestly. Held-out RMSE in kg/ha is 468.6 for M2 (smeared) vs 478.9 for trend-only; M1 is worse at 514.2. (`06_models_fit_stats.csv`.)
15. **Why Duan smearing?** exp(predicted log) underestimates the mean yield, and smearing corrects this. Both versions are reported. (`06_models_final.loyo`.)
16. **Are rainfall and temperature too collinear?** No. The maximum within VIF is 1.58 and the within correlation is -0.485. (`07_diag_collinearity.csv`.)
17. **Is any single district driving the result?** No. Leave-one-district-out gives M2 between -11.60% and -9.41%. (`07_diag_leave_one_district_out.csv`.)
18. **What about the Western Ghats data problems?** Dropping Kolhapur and Sangli gives M2 -11.81% [-18.45%, -5.43%]. (`09_robust_results.csv`; `05c_cases.csv`.)
19. **How would someone reproduce your numbers?** Run `bash run_all.sh`. A deletion-and-rerun test produced byte-identical tables and figures. (`run_all.sh`; `docs/PROGRESS.md` A14 entry.)
20. **What was decided before seeing results, and how do we know?** The model set, verdict rule, headline rule, inference methods, dq_flag rule and robustness list, in dated SPEC amendments written before the final run (A11-A13). The dq_flag rule was kept even though it flagged Buldhana instead of the Ghats. (`docs/SPEC.md`; `docs/notes.md`; `docs/PROGRESS.md`.)

---

## Things this guide could not verify

- The agronomic statements about soybean (why rain and heat matter), and all literature claims in `report/report.md` section 1.2 (e.g. Lobell and Field 2007, Schlenker and Roberts 2009, Maiti et al. 2024/2026, Patil and Shende 2022). Only Lobell et al. 2011 is in `docs/literature/`, and its content was not checked against the report's summary.
- The official district-history facts behind the crosswalk (split dates and parents). They come from the teammate's report and the team lead, not from any file I could check against an official source.
- Whether the ICRISAT extract matches a specific release of the ICRISAT database.
- That the Western Ghats anomalies are caused by gaps in the station network; the code shows only that the values are in IMD's product.
- That the pipeline works on another machine or with another Python version (it was run with Python 3.14.6, `README.md`).
- That changing the crop, period or district rule works as described in Section 8; this was not tested.
- That the IMD server and the imdlib API will stay available.
