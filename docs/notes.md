# Data decisions log (append only)

## 2026-10-18 - initial inspection of data/raw
- ICRISAT headers confirm the units: "SOYABEAN AREA (1000 ha)", "SOYABEAN PRODUCTION (1000 tons)", "SOYABEAN YIELD (Kg per ha)". A pre-check of the values agrees: reported yield equals 1000*production/area to within 0.1 kg/ha (rounding). No unit conversion is needed.
- ICRISAT: 464 rows, 26 districts, years 2000-2017, State Name = Maharashtra only, no missing values. Bombay has 14 years; every other district has 18.
- All 26 ICRISAT district strings match the district-to-subdivision map exactly, including the spellings "Amarawati", "Yeotmal", "Nasik" and "Bombay".
- IMD subdivision file: the four Maharashtra subdivisions cover 1901-2015 with no missing values in 2000-2015. "MATATHWADA" is the file's spelling of Marathwada.
- District rule: counted over 2000-2017, the rule gives exactly the 13 expected districts. Counted only over 2000-2015, Beed (13 qualifying years) and Osmanabad (14) would fail. Decision: count over the full target period 2000-2017, because the rule describes where soybean is grown (it is not a statistical requirement of the fallback window) and the final panel targets 2000-2017. FLAGGED for the user to confirm.
- ERA5 point file (era5_point_temperature.csv): REJECTED for the model. Columns are valid_time, t2m, latitude, longitude. Every row has latitude 19.0 and longitude 73.3 (a single grid point on the Konkan coast, near the Raigad/Thane area). Coverage: hourly, 2000-01-02 00:00 to 2017-12-31 23:00, 157,776 rows. t2m is in Kelvin (range 283.5-315.2 K). Reasons for rejection: (1) one point cannot give district-level variation, so it would be absorbed by the year dimension and confounded with the trend; (2) the point is in the Konkan subdivision, which contains no selected soybean district, so it does not describe soybean-belt conditions in Vidarbha or Marathwada; (3) coastal temperature is moderated by the sea and does not represent the interior Deccan plateau.
- district_wise_rainfall_normal.csv: one long-run normal per district and no yearly values. It is not used in the regression (it has no year-to-year variation).

## 2026-10-18 - src/01_clean_icrisat.py
- Columns renamed by header name: Dist Code->dist_code, Year->year, State Name->state, Dist Name->district, SOYABEAN AREA (1000 ha)->area_kha, SOYABEAN PRODUCTION (1000 tons)->prod_kt, SOYABEAN YIELD (Kg per ha)->yield_kgha. Cotton columns are not used.
- Units confirmed: reported yield equals 1000*prod_kt/area_kha. Largest |diff| = 0.0999 kg/ha (Pune 2017), mean 0.0035, so this is rounding. No conversion applied. Full table: outputs/tables/icrisat_yield_check.csv.
- Zero area: 68 rows (Bombay 14, Raigad/Ratnagiri/Thane 18 each). In every one, production and yield are also 0. Treated as "not grown" and dropped, not as zero yield. No row has area > 0 with yield 0.
- District rule (>=15 years with area >= 20k ha, counted over 2000-2017): 13 districts, identical to the expected list. Borderline exclusions: Aurangabad, Ahmednagar, Nasik and Satara each have 14 qualifying years, one short of the threshold.
- Kept rows in selected districts with area below 20k ha (the rule selects districts; it does not filter rows): Beed 2000 (3.3k ha), 2001 (6.9), 2002 (16.5); Nanded 2000 (10.1); Osmanabad 2000 (9.1), 2001 (17.7). These are early years of soybean expansion in Marathwada. Yields on such small areas may be noisy; worth a sensitivity check later.
- Selected districts by subdivision: Vidarbha 7, Marathwada 4, Madhya Maharashtra 2, Konkan 0.
- District-to-subdivision map written to data/interim/district_subdivision_map.csv from config.DISTRICT_SUBDIVISION (26 districts, all ICRISAT names matched).

## 2026-10-18 - src/02_build_panel_subdivision.py
- Rainfall windows built by summing the IMD monthly columns: R_season = JUN+JUL+AUG+SEP, R_early = JUN+JUL, R_late = AUG+SEP (mm). Cross-check against the file's own "Jun-Sep" column: max |diff| = 0.20 mm (rounding).
- Each district receives its subdivision's rainfall through data/interim/district_subdivision_map.csv. All districts in one subdivision therefore share an identical rainfall series. The 13 districts give only 3 distinct series (Vidarbha 7 districts, Marathwada 4, Madhya Maharashtra 2).
- Restricted to 2000-2015 (IMD ends 2015). ICRISAT 2016-2017 rows are kept in soy_clean.csv but are not in panel_v1.
- ln_yield = natural log of yield_kgha (all yields > 0). trend = year - 2000.
- Subdivision rainfall table written to data/interim/subdivision_rainfall.csv.

## 2026-10-18 - src/03_eda.py
- Outlier rule: district-years more than 3 SD from the district mean, on yield_kgha and on ln_yield. Result: no district-year exceeds 3 SD. The largest is Kolhapur 2005 (z = -2.28 on yield, -2.73 on ln yield). No rows dropped.
- Oddities noted, not acted on: (1) yields collapse across Vidarbha and Marathwada in 2008-2009 and 2014-2015 (state mean ~600-750 kg/ha vs ~1200-1600 in good years), and 2014-15 had low rainfall in Marathwada. (2) The pooled correlation of ln_yield with trend is negative (-0.29) because of the weak 2014-2015 years at the end of the window, so the fitted trend may be negative or close to zero. (3) Madhya Maharashtra (Kolhapur, Sangli) has much higher yields at moderate rainfall, so the pooled yield-rainfall picture mixes levels across subdivisions; district FE are needed. (4) Rainfall series are clearly not independent across subdivisions within a year (2014-15 dry in all three), which matters for the year-clustered SEs.
- 100 mm context: as a share of the mean Jun-Sep total it is 10.4% for Vidarbha (mean 961 mm, SD 190), 16.1% for Marathwada (622, 140) and 12.5% for Madhya Maharashtra (801, 207), i.e. 0.48-0.71 SD. Full table: outputs/tables/eda_subdivision_rainfall_context.csv.
- All EDA CSVs start with a "# PROTOTYPE ..." comment line (read with comment='#'); figures carry the same footer.

## 2026-10-18 - src/04_models_prototype.py
- Rbar for the 100 mm experiment = the subdivision mean over 2000-2015. The script asserts that each district's mean equals its subdivision's mean, which holds because the panel is balanced and rainfall is shared.
- Squared terms use rainfall in mm, so coefficients on squares are ~1e-6. No rescaling was applied, so units stay as in SPEC.
- Bootstrap: years are resampled with replacement (all 13 districts of a drawn year move together). Duplicated years are relabelled by draw position so the panel index stays unique, while each draw keeps its original trend value. 1000 reps, seed 28, 0 failed fits.
- Timing variants: the 100 mm deficit is applied to one window at a time (R_early or R_late), as written in SPEC. A combined split (e.g. 50/50) has not been chosen.
- Oddities (prototype only, for judgement later): (1) the trend is negative in all models (-0.023 to -0.034 per year in ln yield), driven by the poor 2014-15 seasons at the end of the window. (2) In timing_quad, R_late has a convex shape (minimum at 378.5 mm), so a late deficit "raises" yield in Marathwada (+13.9%, CI -14% to +62%). That is implausible agronomically and most likely overfitting: 4 rainfall terms identified from 3 series x 16 years. (3) For timing_quad, year-clustered SEs are much smaller than the bootstrap SEs (R_early: 0.00095 vs 0.00154; R_early_sq: 7.6e-7 vs 1.8e-6). This is consistent with 16 clusters being too few. (4) The quadratic R_season turning point (1269 mm) is inside the observed range only because of Vidarbha's wettest years.

## 2026-10-18 - src/05 skeleton
- The precipitation conversion for ERA5-Land monthly means (m/day x 1000 x days in month) is written in the docstring as the expected case only; the code must read it from the NetCDF attributes. The old-to-new district pairs listed in the docstring (e.g. Washim -> Akola) are hypotheses to verify against the teammate's notes, not decisions.

## 2026-10-18 - team-lead decisions (see SPEC.md Amendments 2026-10-18)
- D1: district set fixed at the 13 districts from the 2000-2017 rule, for every panel. Confirms the earlier interpretation; no data change.
- D2: the six small-area district-years (Beed 2000-02, Nanded 2000, Osmanabad 2000-01) stay in the main models. Robustness: drop rows with area_kha < 20; area-weighted estimation.
- D3: timing-model main scenario = proportional split of the 100 mm by each window's share of the district's mean Jun-Sep rainfall; single-window shocks as sensitivity. The quadratic timing model is exploratory.
- D4: installed xarray 2026.9.0, netCDF4 1.7.5, geopandas 1.2.0, shapely 2.2.0. pip also pulled in their required dependencies (certifi, cftime, pyogrio, pyproj); no other top-level package was installed. Import and smoke tests pass.
- D5: wider robustness set = 13 + Aurangabad, Ahmednagar, Nasik, Satara. These four have soybean area > 0 in all 18 years, so the wider panel stays balanced. Old-to-new district pairs remain UNVERIFIED.
- D6: primary trend = common linear. Robustness: none, district-specific, year FE (year FE only with district-level rainfall).

## 2026-10-18 - build of src/06-09 (prototype runs only)
- New panel column R_julsep = JUL+AUG+SEP (mm) for the alternative-window robustness check. panel_v1.csv was rebuilt; the existing 12 columns are byte-for-byte equal to the previous version (checked with pandas assert_frame_equal).
- New files: soy_clean_wide.csv (306 rows, 17 districts, 2000-2017) and panel_v1_wide.csv (272 rows = 17 x 16). The four extra districts have area > 0 in every year, so no rows were dropped for zero area. Several of their years have area < 20k ha (that is why they fail the rule); those rows are kept.
- src/08 kg/ha conversion for ln models: kg/ha = pct x Ybar_d, where Ybar_d = the district's mean observed yield over the panel years. This is a choice; flagged in HANDOFF.
- src/08 subdivision and state rows = unweighted mean of district rows, computed inside each bootstrap replication.
- src/08 range curve: R runs from min(R_season)+100 to max(R_season), so both R and R-100 are inside the observed range (no extrapolation).
- src/09 year-FE variant skipped on panel_v1 because rainfall is subdivision-level (SPEC A6). Detection is data-based: R_season constant within every subdivision-year.
- src/09 drop_small_area removes 6 rows: Beed 2000-2002, Nanded 2000, Osmanabad 2000-2001.

## 2026-10-19 - team-lead amendments A7-A10 (see SPEC.md)
- A7: headline intervals switch from the iid year bootstrap to a moving-block bootstrap over years (L = 3; sensitivity 2, 4; 2000 reps; seeds in config.BOOT_SEEDS). Reason: src/07 found serial correlation within districts (Wooldridge p = 0.003) and strong common year shocks (Pesaran CD = 12.8). Resampling blocks of consecutive years keeps both the cross-district dependence within a year and short-run dependence across years. Coefficients will also be reported with district, year, two-way and Driscoll-Kraay SEs plus a wild cluster bootstrap.
- A8: report headings replaced by the professor's required structure.
- A9: kg/ha baseline = district mean observed yield over panel years (the rule already used in src/08, now confirmed). Duan smearing shown with and without for every log-to-kg/ha prediction. The percent effect needs no smearing: with a constant smearing factor it cancels in the ratio.
- A10: crosswalk statuses as listed in SPEC A10. The CONFIRMED_OFFICIAL_PAGE source is the teammate's report citing official district-history pages; neither the team lead nor I has checked those pages. Jalna is mapped to Aurangabad; its Partur taluka came from Parbhani (CAVEAT), so a whole-district dissolve slightly misallocates Partur.
- Renamed districts (my addition, flagged): current boundary files may use the new names Dharashiv (= Osmanabad), Chhatrapati Sambhajinagar (= Aurangabad) and Ahilyanagar (= Ahmednagar). These are renames, not splits. The team lead did not list them, so they are recorded as UNVERIFIED. The guard only blocks if the boundary file actually uses those names.

## 2026-10-19 - implementation of A7-A10 (prototype runs only)
- Moving-block bootstrap: non-circular, ceil(T/L) block starts drawn uniformly from 0..T-L, truncated to T years. Each drawn year carries all its districts and keeps its original trend value. src/06 and src/08 use the same draws (same seeds). The full model (district effects, trend, rainfall) is refitted in every replication by an array within-estimator (pipeline_utils.FastFE), asserted equal to PanelOLS on the full sample.
- Percentile p-value for bootstrap tests: p = 2 x min(share of draws <= 0, share >= 0).
- Wild cluster bootstrap: WCR bootstrap-t (null imposed), clusters = districts, Rademacher weights. With 13 districts all 2^13 = 8192 sign vectors are enumerated, so the p-value is exact and needs no seed. Not computed for the trend coefficient.
- Driscoll-Kraay: linearmodels cov_type="kernel", Bartlett, bandwidth 2 = lags 0..2 with weights 1, 2/3, 1/3. Checked against a hand computation: identical up to linearmodels' n/(n-k) small-sample factor (k = 16 incl. district effects).
- The iid year bootstrap used on 2026-10-18 in src/08 is replaced by the MBB (A7). Point estimates are unchanged (checked: all 306 rows of 08_scenario_results identical in pct and kg/ha).
- Prototype finding: with the MBB (L = 3) the linear rainfall coefficient has p = 0.067, and the linear 100 mm interval at state level includes zero ([-15.4%, +0.8%]). With L = 4 it excludes zero ([-15.6%, -1.2%]).
- Prototype finding: the linear-vs-quadratic verdict is INCONCLUSIVE for both outcomes. The squared term is significant with district-clustered SEs, the wild bootstrap and Driscoll-Kraay, but not with year-clustered, two-way or the MBB.
- Duan smearing (A9): smearing makes the kg/ha held-out RMSE of the log models worse, not better (linear 541 -> 561; quadratic 525 -> 544), because the mean smearing factor (about 1.09) inflates predictions. Both log models stay worse than the trend-only model either way; the kg/ha (level) models beat it.
- Area weighting (A9), prototype: (1) weight concentration is moderate: Kish effective number of districts 11.0 of 13. But Madhya Maharashtra (Kolhapur, Sangli) gets only 5.1% of the weight, and years after 2007 get 62.8% (vs 50%). (2) Kolhapur and Sangli have the only non-negative district-specific 100 mm effects (+7.4%, +1.6%), and slope correlates with area share (r = 0.48). (3) Decomposition: cross-district weights alone move the effect from -9.9% to -12.1%; the within-district time profile alone to -11.5%; together -13.2%. So both channels matter. (4) No single district drives it: leave-one-district-out under weights stays between -12.7% and -14.1%.
- Boundary variant (A10): dropping Akola, Parbhani, Osmanabad and Chandrapur gives linear -8.4% [-14.2, -2.2] and quadratic -11.0% (delta-method, year-clustered), vs base -9.9% and -12.8%.
- Crosswalk (A10): implemented in config.DISTRICT_CROSSWALK and src/05 crosswalk_table() / check_crosswalk(). Tested without gridded data: refuses on an UNVERIFIED pair that is used, an unmapped current district, or a panel district without a polygon; passes when the UNVERIFIED pairs are unused.
- src/03 converted to a CLI. Its 10 outputs on panel_v1 are byte-identical (CSV) and pixel-identical (PNG) to the 2026-10-18 versions in outputs/tables and outputs/figures. New runs write to outputs/prototype/. The old copies in outputs/tables and outputs/figures are left in place.
