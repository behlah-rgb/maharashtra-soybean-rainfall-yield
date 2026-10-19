# Specification of record

Written: 2026-10-18 (before any model was fitted). Changes need the user's approval and are appended below with a date.

## Data and period
- Crop: soybean (ICRISAT district-level data, Maharashtra, older district boundaries).
- Target period: 2000-2017 (the full ICRISAT period).
- Fallback (prototype) panel: 2000-2015, because IMD subdivision rainfall ends in 2015.

## Districts
- Rule: keep districts with at least 15 years in which soybean area >= 20 thousand ha. The rule is derived from the data, not hard-coded.
- Interpretation (see docs/notes.md 2026-10-18): the rule counts years over the full target period 2000-2017. The resulting list is then used for both the fallback and the final panel.
- Expected list (user): Akola, Amarawati, Beed, Buldhana, Chandrapur, Kolhapur, Nagpur, Nanded, Osmanabad, Parbhani, Sangli, Wardha, Yeotmal. Any difference is reported by src/01.
- Zero soybean area means "not grown", not a real zero yield. Those rows are dropped.

## Variables
- Outcome: ln(yield), yield in kg/ha. Robustness outcome: yield in kg/ha.
- Weather (mm): R_season = Jun+Jul+Aug+Sep rainfall; R_early = Jun+Jul; R_late = Aug+Sep.
- Temperature is not available in the fallback panel, so the prototype uses rainfall only.
- Trend: t = year - 2000.

## Models (d = district, t = year)
- Linear: ln Y_dt = a_d + g*t + b1*R_dt + e_dt
- Quadratic: ln Y_dt = a_d + g*t + b1*R_dt + b2*R_dt^2 + e_dt
- Timing variant: replace R with R_early and R_late (linear), or with R_early, R_early^2, R_late and R_late^2 (quadratic).
- Estimation: linearmodels PanelOLS with district (entity) fixed effects plus a linear trend.

## 100 mm deficit experiment
- Change in ln Y = f(Rbar_d - 100) - f(Rbar_d), where f is the fitted rainfall part of the model and Rbar_d is the district's mean rainfall. Percent change = exp(change) - 1.
- Linear model: this equals exp(-100*b1) - 1 and does not depend on Rbar_d.
- In the prototype, Rbar is the subdivision's mean, because every district in a subdivision has the same rainfall series.
- Timing variant: the 100 mm deficit is applied to the season total. Splitting it between the early and late windows needs a choice that has not been made yet (see HANDOFF.md). The prototype reports the deficit applied to each window separately.

## Inference
- Standard errors clustered by year, as a stopgap.
- Bootstrap: resample whole years with replacement, 1000 replications, seed from config.py; percentile intervals.
- Limitation, stated plainly: in the fallback panel, rainfall is at IMD subdivision level. The selected districts fall in only three subdivisions (Madhya Maharashtra, Marathwada, Vidarbha), so there are only three independent rainfall series. The effective rainfall variation is three series x 16 years, not 13 districts x 16 years, and the standard errors overstate precision. With 16 year-clusters, the clustered standard errors are themselves unreliable.
- Results are associations under the model's assumptions. Fixed effects remove confounding by time-invariant district traits only.

## Status of outputs
- Every output from the subdivision panel carries the header "PROTOTYPE - NOT FOR THE REPORT: rainfall is subdivision-level and has no temperature."
- Only the final gridded panel (src/05, panel_final.csv) may feed the report.

## Data rejected for the model
- district_wise_rainfall_normal.csv: one long-run normal per district and no yearly values, so it cannot identify year-to-year effects. Not used in the regression.
- era5_point_temperature.csv: a single grid point, rejected (see docs/notes.md).

## Amendments 2026-10-18 (decisions from the team lead)

A1. **District set.** Defined once, from the full ICRISAT window 2000-2017, and used for every panel (fallback and final): the 13 districts. Reason: the set describes where soybean is grown in the target period and must not change with the rainfall source's coverage.

A2. **Small-area district-years.** The six district-years with area < 20 thousand ha (Beed 2000-2002, Nanded 2000, Osmanabad 2000-2001) stay in the main models. Robustness: (a) drop district-years with area < 20 thousand ha; (b) area-weighted estimation (weights = area_kha).

A3. **Timing models.** Main timing scenario: the 100 mm deficit is split across Jun-Jul and Aug-Sep in proportion to each window's share of the district's mean Jun-Sep rainfall (deficit_early = 100 x Rbar_early,d / Rbar_season,d; deficit_late = 100 - deficit_early). Sensitivity: each window alone. The quadratic timing model is exploratory only. **Headline models: linear and quadratic in R_season.**

A4. **Packages.** xarray, netCDF4, geopandas and shapely are added to .venv and pinned in requirements.txt. Nothing else.

A5. **District rule fixed at 13.** Robustness: a wider set that adds Aurangabad, Ahmednagar, Nasik and Satara (each one qualifying year short). Old-to-new district pairs stay marked UNVERIFIED in code and docs until the teammate confirms them.

A6. **Trend specification (locked before seeing gridded results).** Primary: a common linear trend (t = year - 2000). Robustness: no trend; district-specific linear trends; year fixed effects (only when rainfall is district-level, because with subdivision rainfall year effects would absorb most of the rainfall variation). Note: the negative trend in the prototype is driven by the poor 2014-15 seasons at the end of the 2000-2015 window. It must be re-examined when 2016-2017 are added in the final panel.

Additional specification items implied by the build requested with these amendments (src/06-09):
- Model comparison: F-test on squared terms (clustered Wald and classical F), within R2, AIC/BIC from the Gaussian log-likelihood of the within model, and leave-one-year-out prediction error. Robustness outcome yield in kg/ha is fitted in src/06.
- Scenarios (src/08): the 100 mm deficit per district and per subdivision at each district's mean rainfall and across the observed rainfall range. Bootstrap by years (main) and by districts (check). Illustrative weak-monsoon scenarios at 90% and 80% of each district's mean rainfall. Results in percent and in kg/ha.
- Robustness (src/09): A2a, A2b, A5 wider set, A6 trend variants, alternative rainfall windows (Jun-Jul, Jul-Sep, Jun-Sep), and dropping each drought year (2009, 2014, 2015) in turn.

## Amendments 2026-10-19 (team lead, A7-A10)

A7. **Inference.**
- Headline intervals: moving-block bootstrap (MBB) over years. Whole years are resampled in blocks of consecutive years, with all districts of a year together. The full model (district effects + common trend + rainfall terms) is refitted in every replication. Block length 3; sensitivity 2 and 4; 2000 replications; seeds recorded in config.py (BOOT_SEEDS). This replaces the iid year bootstrap of src/08 (2026-10-18) as the headline interval. The district bootstrap stays as a check.
- Reported side by side for the coefficients: district-clustered SEs (plus a wild cluster bootstrap by district), year-clustered, two-way clustered (district and year), and Driscoll-Kraay (Bartlett kernel, maxlags 2). Driscoll-Kraay is flagged as unreliable at T = 18 (and at T = 16 in the prototype).
- Linear vs quadratic: the conclusion on the squared term must be the same under every one of these methods (district-clustered, wild cluster bootstrap, year-clustered, two-way, Driscoll-Kraay, MBB L = 3) at the 5% level. Otherwise it is reported as INCONCLUSIVE. MBB L = 2 and 4 are reported as sensitivity.

A8. **Report structure (professor's required format).** Main sections, verbatim: 1 Assumptions; 2 Estimates of parameters; 3 Numerical experiments; 4 Stability analysis; 5 Conclusion; then References and Appendix. Subsections: 1.1 Problem and research question; 1.2 Background and literature; 1.3 Data sources and panel construction; 1.4 Variables; 1.5 Model formulation; 1.6 Statistical and causal assumptions; 2.1 Estimation method; 2.2 Linear estimates; 2.3 Quadratic estimates; 2.4 Linear vs quadratic comparison; 2.5 Goodness of fit and interpretation; 3.1 100 mm deficit; 3.2 Weak-monsoon scenarios; 3.3 Response curves; 4.1 Residual diagnostics; 4.2 Leave-one-out stability; 4.3 Robustness (windows, weighting, standard errors, boundary variants); 5 Conclusion, including limitations and causal caveats. Supersedes the 16-heading skeleton of 2026-10-18.

A9. **kg/ha and follow-ups.**
- Percent is the headline unit. kg/ha baseline = the district's mean observed yield over the panel years, stated wherever kg/ha is used.
- When log-model predictions are converted to kg/ha (including the held-out comparison with the trend-only model), Duan's smearing correction is applied. Results are shown with and without it.
- Investigate why area weighting moves the 100 mm effect most: weight concentration and district-level effects.
- Re-examine the negative trend once 2016-2017 are in the final panel.

A10. **Crosswalk guard.** Old-to-new district pairs carry a status:
- CONFIRMED_OFFICIAL_PAGE: Latur->Osmanabad, Gadchiroli->Chandrapur, Nandurbar->Dhule, Hingoli->Parbhani, Gondia->Bhandara, Jalna->Aurangabad, Palghar->Thane. Source: Maharashtra government district-history pages cited in the teammate's report. Not independently verified by the team lead or by me.
- CAVEAT: Washim->Akola (parent area needs taluka-level confirmation); Jalna also took Partur taluka from Parbhani.
- Any other pair stays UNVERIFIED. The build refuses to write panel_final.csv only if a pair it uses is UNVERIFIED.
- Robustness (src/09): drop Akola, Parbhani, Osmanabad and Chandrapur (the selected districts whose old boundaries include a later split).

Also (team lead, 2026-10-19): keep the Pesaran CD test in src/07. src/03_eda.py takes a panel path and output folder with the same outputs/final guard.

## Amendments 2026-10-19 (team lead, A11)

A11.1 **Verdict scope and pre-specified headline rule (fixed before any gridded result).** The linear-vs-quadratic verdict uses district-, year- and two-way clustered SEs, the wild cluster bootstrap, Driscoll-Kraay and the moving-block bootstrap at L = 3. L = 2 and L = 4 are sensitivity only. If the verdict is INCONCLUSIVE, the headline 100 mm effect is the LINEAR model's (fewer parameters), the quadratic is reported beside it as sensitivity, and the report states the range across both. If QUADRATIC SUPPORTED, the quadratic is headline; if LINEAR ADEQUATE, the linear. This rule must not be changed after seeing results.

A11.2 **Renames are aliases.** Dharashiv = Osmanabad, Chhatrapati Sambhajinagar = Aurangabad, Ahilyanagar = Ahmednagar: status ALIAS_NAME_ONLY (name change, same boundary). The guard never blocks on them. If a boundary layer uses the new names, map by alias and sanity-check each matched polygon (area, centroid) against the old-name polygon in the 2011 Census layer.

A11.3 **Partur.** No taluka-level handling. Jalna stays wholly in Aurangabad. Limitation: old Parbhani loses Partur taluka. The drop-four-districts run (A10) covers boundary sensitivity.

A11.4 **Washim -> Akola** set to CONFIRMED_OFFICIAL_PAGE (verified by the team lead from the Central Ground Water Board Washim document and the Akola district website history page: Washim carved from Akola on 1 July 1998). Its CAVEAT is removed. The Partur caveat for Jalna/Parbhani stays.

A11.5 **Outputs.** outputs/prototype is the home of prototype outputs. Only outputs/final may feed the report.

## Amendments 2026-10-19 (team lead, A12: weather data acquired by us; written before any weather value was computed)

A12.1 **Context.** The teammate did not deliver data. We acquire the weather data ourselves, with no Copernicus account. Final panel: district-level rainfall and temperature for the 13 soybean districts, 2000-2017 (234 rows), plus the 17-district wider set for robustness (306 rows).

A12.2 **Sources.** IMD gridded daily data via imdlib (`imdlib.load`, archive source): rainfall 0.25 deg (Pai et al. 2014), Tmax and Tmin 1.0 deg, 2000-2017, cached unchanged in data/raw/grids/imd/. Boundaries: DataMeet maps repository, Districts/Census_2011/2011_Dist (2011 Census districts; Maharashtra has 35), pinned to a commit. GADM level 2 only if DataMeet fails. Emergency fallback for temperature only: NASA POWER daily T2M_MAX/T2M_MIN at district centroids, ONLY with the user's approval. No other source may be substituted; if a download fails twice, stop. ERA5 is not used.

A12.3 **Old districts.** Old ICRISAT district = union of current (2011) districts: Akola = Akola + Washim; Parbhani = Parbhani + Hingoli; Osmanabad = Osmanabad + Latur; Chandrapur = Chandrapur + Gadchiroli; Bhandara = Bhandara + Gondia; Dhule = Dhule + Nandurbar; Aurangabad = Aurangabad + Jalna; Thane = Thane (+ Palghar if present). The others map to themselves, allowing only listed spelling variants (Amravati/Amarawati, Yavatmal/Yeotmal, Nashik/Nasik, Ahmadnagar/Ahmednagar, plus the A11 aliases). Unmatched names stop the build. Stored in data/interim/old_to_current_districts.csv; dissolved polygons in data/interim/old_districts.gpkg. Limitations: Partur taluka (Jalna, from Parbhani) and Washim's parent area at taluka level.

A12.4 **Spatial aggregation.** For each old district, the daily district value is the area-weighted mean over grid cells, with weight = area of overlap between the grid cell (a lon-lat box centred on the cell centre, in an equal-area projection) and the district polygon. This is the fractional-overlap method. Cells with missing values on a day are dropped and the weights renormalised over the valid cells. Because a 1.0 deg temperature cell is larger than many districts, fractional overlap uses every cell that touches the district, so no district is without cells. If a district has no valid overlapping cell on a day, the nearest valid cell centre is used and logged. The same method is used for rainfall and temperature.

A12.5 **Variables** (district d, year t; season = 1 Jun to 30 Sep, 122 days):
- R_season = sum over 1 Jun-30 Sep of daily district-mean rainfall (mm); R_early = 1 Jun-31 Jul; R_late = 1 Aug-30 Sep; R_julsep = 1 Jul-30 Sep (kept so the panel has the same columns as panel_v1).
- dry_spell_max = longest run of consecutive days, within 1 Jun-30 Sep, with district-mean daily rainfall < 2.5 mm (days).
- T_season = mean over 1 Jun-30 Sep of daily (Tmax + Tmin)/2 of the district means (deg C). District Tmax and Tmin are aggregated separately, then averaged.
- ln_yield, yield_kgha, area_kha, prod_kt from data/processed/soy_clean.csv; trend = year - 2000; subdivision from the district map.
- panel_final.csv: the panel_v1.csv columns plus dry_spell_max and T_season. Assert 13 x 18 = 234 rows, unique (district, year), no missing values.

A12.6 **Validation (src/05b) before any model:** (a) gridded vs IMD subdivision R_season 2000-2015 (correlation, mean ratio); (b) old-district mean R_season vs area-weighted district normals (flag > 25%); (c) plausibility of T_season, units and missing cells; (d) corr(R_season, T_season), VIF, cross-district rainfall correlation and the effective number of independent rainfall signals; (e) descriptive yield vs R_season and yield by year including 2016-2017.

## Amendments 2026-10-19 (team lead, A13; the team lead labelled this set "A12", renumbered here because A12 is already the weather-acquisition amendment). Fixed before any final model is run; not to be changed after seeing results.

A13.1 **Crosswalk.** Washim -> Akola: CONFIRMED_OFFICIAL_PAGE; source column = team lead, from the Central Ground Water Board Washim document and the Akola district website (Washim carved from Akola on 1 July 1998). The Yavatmal mention in the teammate's report is the 1905 history; no adjustment to old Yeotmal. Jalna/Parbhani Partur caveat kept. Other rows keep "via teammate report, not independently verified". "MUMBAI SUB" = Mumbai Suburban accepted.

A13.2 **Headline model set** (supersedes the rainfall-only headline models). ln(yield), district fixed effects, common linear trend (A6). Centring: Rc = (R_season - grand mean) / 100 (unit = 100 mm), Tc = T_season - grand mean (deg C), grand means over the panel's district-years, then squared. Coefficients are therefore per 100 mm and per 1 deg C (in M2: the marginal effect at the grand mean).
- M1 linear: Rc, Tc.
- M2 quadratic: Rc, Rc^2, Tc, Tc^2.
- Exploratory only: timing model (R_early, R_late per 100 mm, centred; dry_spell_max; Tc); quadratic-in-rainfall-only (Rc, Rc^2, Tc).
- Robustness outcome yield in kg/ha (M1_level, M2_level) kept from SPEC.
- Linear vs quadratic = joint test of Rc^2 and Tc^2 (q = 2) under each A7/A11 method (district CR, wild cluster bootstrap, year CR, two-way CR, Driscoll-Kraay, MBB L = 3); headline rule A11.1 (INCONCLUSIVE -> M1 headline, M2 beside it, report the range).

A13.3 **100 mm experiment.** Headline (variant A): T_season held at each district's mean (ceteris paribus). Exploratory variant B: T moves with rainfall, T_new = Tbar_d + s_d (R_new - Rbar_d), where s_d is district d's within-district OLS slope of T_season on R_season; s_d is re-estimated in every bootstrap replication. Both reported as percent change and kg/ha (baseline = district mean observed yield, A9). Weak-monsoon scenarios at 90% and 80% of each district's mean rainfall, both variants. Intervals: moving-block bootstrap over years (A7).

A13.4 **Data quality, written before results.**
- a. Diagnose first (src/05c_diagnose_ghats.py -> outputs/final/tables): every panel district-year with |R_season - district median| > 3 robust SD (robust SD = 1.4826 x MAD over the district's 18 years), plus Ratnagiri 2008, Raigad 2008, Pune 2005. Report: maximum daily cell value, cells over 300 mm/day, fill/sentinel values in the raw grid, gridded total vs IMD subdivision total (years <= 2015), and how imdlib treats missing-value sentinels.
- b. If the cause is a processing bug: fix the build, document it, rebuild panel_final.csv, rerun src/05b, and STOP before any model.
- c. If it is a property of the IMD data: keep all 13 districts in the primary run and add a column dq_flag. Rule (fixed now): dq_flag = 1 for every panel district-year meeting the screening criterion in (a) (|robust z| > 3), else 0; same rule for the 17-district wide panel.
- d. Robustness (src/09): drop Kolhapur and Sangli; drop 2000-2003; drop dq_flag district-years; drop Akola, Parbhani, Osmanabad, Chandrapur (A10); year fixed effects instead of the trend (exploratory, allowed now that rainfall is district-level); the wide 17-district panel; area weighting; alternative rainfall windows; drop each drought year. The A2/A6 robustness runs stay. Cotton is out of scope.
- e. Re-examine the sign of the trend now that 2016-2017 are included, and report it.

A13.5 **To carry into the report.** About 2.6 effective independent rainfall signals (src/05b (d)); the 1-degree temperature grid (several districts share cells; 7 old districts contain no cell centre); IMD rainfall in the Western Ghats zone is less reliable.

## Amendments 2026-10-19 (team lead, A14). Headline models and rules unchanged.

A14.1 **Year fixed effects** are a prominent stability result, not a failed check. Add a variance-share analysis: for district-demeaned R_season and T_season, the share of variance explained by year dummies (the part of within-district variation common across districts in a year). Report M1 and M2 year-FE estimates with moving-block bootstrap intervals (L = 3, 2000 reps).
A14.2 **dq_flag** stays as applied; document that it flagged Buldhana wet years, not the Ghats districts. Not redefined.
A14.3 **Robustness intervals.** Moving-block bootstrap (L = 3, 2000 reps, seed BOOT_SEEDS['block_L3']) for: year-FE M1/M2, drop Kolhapur + Sangli M1/M2, area-weighted M1/M2. All other rows keep the delta method. The robustness table gets an "interval_method" column.
A14.4 **Prototype outputs** stay in outputs/prototype as historical records; README notes that src/06-09 require panel_final.csv.
A14.5 **Sanity checks** (outputs/final/tables): (a) independent numpy recomputation of the headline 100 mm effect from the stored M2 coefficients vs src/08; (b) turning points for R and T, share of observations on each side, within-district SD of R and T; (c) response curves of ln(yield) vs rainfall for a dry, a median and a wet district, and vs temperature, with a rug of observed values; (d) M1 and M2 yield change for a 100 mm SURPLUS (symmetry check).
A14.6 **Reproducibility.** run_all.sh runs the pipeline in order from data/raw (flag to skip downloads if the grids exist). Test: delete data/processed and outputs/final, rerun, compare all output tables by checksum with the pre-delete versions; log pass/fail.
A14.7 **docs/REPORT_INPUTS.md**: tables and figure lists only, one-line captions, no interpretation.
