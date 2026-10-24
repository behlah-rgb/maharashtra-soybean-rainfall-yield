# Monsoon rainfall and soybean yield in Maharashtra: linear and quadratic district panel models

<!-- Group 28, mathematical modelling course. Deadline 26 Oct 2026. Structure: professor's required format
     (docs/SPEC.md amendment A8, 2026-10-19).
     SKELETON ONLY. No results are written yet. Every number must come from outputs/final/ (built from
     data/processed/panel_final.csv). Nothing from outputs/prototype/ or any PROTOTYPE log may appear here.
     Percent is the headline unit; wherever kg/ha is used, state: baseline = district mean observed yield over
     the panel years (A9). Describe results as associations under the model's assumptions, never as causal effects. -->

## 1 Assumptions

### 1.1 Problem and research question
<!-- No script output. Question, motivation, why a 100 mm deficit. Specification of record: docs/SPEC.md. -->

### 1.2 Background and literature
<!-- No script output. Sources in docs/literature/ (e.g. Lobell et al. 2011). Rainfed soybean in Maharashtra. -->

### 1.3 Data sources and panel construction
<!-- src/01_clean_icrisat.py -> outputs/tables/icrisat_audit.csv, outputs/tables/icrisat_yield_check.csv;
     src/05_build_panel_gridded.py -> data/processed/panel_final.csv (IMD 0.25 deg rainfall, ERA5-Land temperature,
     district polygons dissolved to ICRISAT districts; crosswalk statuses from config.DISTRICT_CROSSWALK, A10);
     docs/notes.md (rejected ERA5 point file and district normals). -->

### 1.4 Variables
<!-- docs/data_dictionary.md; src/03_eda.py data/processed/panel_final.csv outputs/final ->
     outputs/final/tables/eda_summary_stats.csv, eda_subdivision_rainfall_context.csv;
     outputs/final/figures/eda_mean_yield_by_year.png, eda_yield_heatmap.png, eda_rainfall_by_subdivision.png,
     eda_yield_vs_rseason.png, eda_correlation_matrix.png. -->

### 1.5 Model formulation
<!-- docs/SPEC.md A13.2 (supersedes the rainfall-only models): M1 linear in Rc, Tc; M2 quadratic in Rc, Tc (centred at
     grand means; per 100 mm and per deg C); district effects + common linear trend (A6); ln(yield); kg/ha robustness
     outcome; exploratory timing and rain-only-quadratic models. Headline rule A11.1 (06_models_linear_vs_quadratic.csv). -->

### 1.6 Statistical and causal assumptions
<!-- docs/SPEC.md (A6, A7). Strict exogeneity of rainfall given district effects and trend; what fixed effects do and do
     not remove; dependence across districts within a year and over time (motivates A7 inference);
     src/07_diagnostics.py -> outputs/final/tables/07_diag_tests.csv for the evidence. -->

## 2 Estimates of parameters

### 2.1 Estimation method
<!-- src/06_models_final.py -> outputs/final/logs/06_models.txt (PanelOLS; moving-block bootstrap over years, L = 3,
     sensitivity 2 and 4, 2000 reps, seeds in config.BOOT_SEEDS; district/year/two-way clustered, wild cluster bootstrap,
     Driscoll-Kraay flagged unreliable at T = 18; AIC/BIC formula). -->

### 2.2 Linear estimates
<!-- src/06_models_final.py -> outputs/final/tables/06_models_coefficients.csv, 06_models_se_comparison.csv
     (model = linear; linear_level as robustness outcome). -->

### 2.3 Quadratic estimates
<!-- src/06_models_final.py -> outputs/final/tables/06_models_coefficients.csv, 06_models_se_comparison.csv
     (model = quadratic; quadratic_level as robustness outcome); turning point in 06_models_fit_stats.csv. -->

### 2.4 Linear vs quadratic comparison
<!-- src/06_models_final.py -> outputs/final/tables/06_models_linear_vs_quadratic.csv (verdict: QUADRATIC SUPPORTED /
     LINEAR ADEQUATE / INCONCLUSIVE across all inference methods, A7), 06_models_fit_stats.csv (AIC/BIC). -->

### 2.5 Goodness of fit and interpretation
<!-- src/06_models_final.py -> outputs/final/tables/06_models_fit_stats.csv (within R2, leave-one-year-out RMSE, naive
     and Duan-smeared kg/ha vs trend-only, A9), 06_models_loyo_by_year.csv. Re-examine the trend sign now that
     2016-2017 are included (A6, A9). -->

## 3 Numerical experiments

### 3.1 100 mm deficit
<!-- A13.3: variant A (T fixed) is the headline; variant B (T moves with R) exploratory. Summary: docs/RESULTS_SUMMARY.md. -->
<!-- src/08_scenario_100mm.py -> outputs/final/tables/08_scenario_results.csv (scenario = deficit_100mm; district,
     subdivision and state rows; MBB L = 3 headline intervals, L = 2/4 and district bootstrap as checks; timing models:
     deficit_100mm_split main, single windows sensitivity, timing_quad exploratory);
     outputs/final/figures/08_scenario_district_effects.png. -->

### 3.2 Weak-monsoon scenarios
<!-- src/08_scenario_100mm.py -> outputs/final/tables/08_scenario_results.csv (scenario = weak_monsoon_90pct,
     weak_monsoon_80pct; label ILLUSTRATIVE). -->

### 3.3 Response curves
<!-- src/08_scenario_100mm.py -> outputs/final/tables/08_scenario_range_curve.csv;
     outputs/final/figures/08_scenario_range_curve.png. -->

## 4 Stability analysis

### 4.1 Residual diagnostics
<!-- src/07_diagnostics.py -> outputs/final/tables/07_diag_tests.csv (Breusch-Pagan, Brown-Forsythe, Jarque-Bera,
     Wooldridge AR(1), Pesaran CD), 07_diag_influence.csv; outputs/final/figures/07_diag_resid_vs_fitted.png,
     07_diag_qq.png, 07_diag_resid_by_year.png, 07_diag_resid_by_district.png. -->

### 4.2 Leave-one-out stability
<!-- src/07_diagnostics.py -> outputs/final/tables/07_diag_leave_one_district_out.csv,
     outputs/final/figures/07_diag_leave_one_district_out.png; src/06_models_final.py ->
     outputs/final/tables/06_models_loyo_by_year.csv (leave one year out). -->

### 4.3 Robustness (windows, weighting, standard errors, boundary variants)
<!-- Data quality (A13.4): src/05c_diagnose_ghats.py -> outputs/final/tables/05c_cases.csv, 05c_imdlib_masking.csv,
     05c_sentinel_scan.csv; validation outputs/tables/validation_*.csv. Carry A13.5 caveats (2.6 rainfall signals,
     1-degree temperature grid, Western Ghats rainfall reliability). -->
<!-- Windows, sample, trend, drought years, wider district set, boundary variant (drop Akola, Parbhani, Osmanabad,
     Chandrapur): src/09_robustness.py -> outputs/final/tables/09_robust_results.csv, 09_robust_skipped.csv,
     outputs/final/figures/09_robust_forest.png.
     Weighting: src/09_robustness.py -> outputs/final/tables/09_robust_weight_shares.csv,
     09_robust_weighting_decomposition.csv, 09_robust_district_slopes.csv, 09_robust_weighted_leave_one_district_out.csv,
     outputs/final/figures/09_robust_area_weighting.png.
     Standard errors: src/06_models_final.py -> outputs/final/tables/06_models_se_comparison.csv. -->

## 5 Conclusion
<!-- Summary of sections 2-4, including limitations and causal caveats: associations under the model's assumptions;
     fixed effects remove only time-invariant district confounders; few years for time-dependence corrections;
     old district boundaries and crosswalk statuses (CAVEAT rows: Washim-Akola, Partur taluka); temperature only from
     ERA5-Land; irrigation not controlled unless supplied. No new numbers. -->

## References
<!-- Unnumbered back matter. -->

## Appendix
<!-- Reproducibility: README.md run commands; requirements.txt; config.py seeds (BOOT_SEEDS); docs/SPEC.md amendments;
     docs/HANDOFF.md data issues. Optional extra tables from outputs/final/tables/. -->
