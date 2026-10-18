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
