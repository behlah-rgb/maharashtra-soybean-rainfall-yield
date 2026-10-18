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
