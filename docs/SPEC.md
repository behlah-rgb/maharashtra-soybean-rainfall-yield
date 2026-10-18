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
