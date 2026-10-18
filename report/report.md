# Monsoon rainfall and soybean yield in Maharashtra: linear and quadratic district panel models

<!-- Group 28, mathematical modelling course. Deadline 26 Oct 2026.
     SKELETON ONLY. No results are written yet. Every number must come from outputs/final/ (built from
     data/processed/panel_final.csv). Nothing from outputs/prototype/ or the PROTOTYPE logs may appear here.
     Describe results as associations under the model's assumptions, never as causal effects. -->

## 1. Abstract
<!-- Feeds from: src/06_models_final.py -> outputs/final/tables/06_models_coefficients.csv, 06_models_fit_stats.csv;
     src/08_scenario_100mm.py -> outputs/final/tables/08_scenario_results.csv (state row, deficit_100mm). Written last. -->

## 2. Introduction and research question
<!-- No script output. Question, motivation, why a 100 mm deficit. Specification of record: docs/SPEC.md. -->

## 3. Background and literature
<!-- No script output. Sources in docs/literature/ (e.g. Lobell et al. 2011). Soybean in rainfed Maharashtra. -->

## 4. Study area and crop calendar
<!-- src/03_eda.py (rerun on panel_final.csv) -> figures of the district set; Jun-Jul vs Aug-Sep windows from config.py;
     district list and subdivisions from data/interim/district_subdivision_map.csv. -->

## 5. Data sources
<!-- docs/data_dictionary.md; docs/notes.md; src/05_build_panel_gridded.py (IMD 0.25 deg rainfall, ERA5-Land temperature,
     district boundaries, old-to-new district map). Explain why the ERA5 point file and district normals were rejected. -->

## 6. Data processing and panel construction
<!-- src/01_clean_icrisat.py -> outputs/tables/icrisat_audit.csv, icrisat_yield_check.csv;
     src/05_build_panel_gridded.py -> data/processed/panel_final.csv (rows, years, cells per district). -->

## 7. Exploratory data analysis
<!-- src/03_eda.py on panel_final.csv -> summary stats, mean yield by year, heatmap, yield vs rainfall,
     rainfall series, correlation matrix, outlier table, rainfall context for the 100 mm shock. -->

## 8. Model specification
<!-- docs/SPEC.md (models, Amendments 2026-10-18 A3 and A6). Linear and quadratic in R_season with district effects
     and a common linear trend; ln(yield) outcome; robustness outcome kg/ha. -->

## 9. Estimation and inference
<!-- src/06_models_final.py log -> outputs/final/logs/06_models.txt (PanelOLS, year-clustered SEs, AIC/BIC formula);
     src/08_scenario_100mm.py (bootstrap over years, check over districts). -->

## 10. Results: linear and quadratic models
<!-- src/06_models_final.py -> outputs/final/tables/06_models_coefficients.csv, 06_models_fit_stats.csv. -->

## 11. Model comparison and validation
<!-- src/06_models_final.py -> outputs/final/tables/06_models_fit_stats.csv (F-test on squared term, within R2, AIC/BIC,
     LOYO RMSE), 06_models_loyo_by_year.csv. -->

## 12. Diagnostics
<!-- src/07_diagnostics.py -> outputs/final/tables/07_diag_tests.csv, 07_diag_influence.csv,
     07_diag_leave_one_district_out.csv; figures 07_diag_resid_vs_fitted.png, 07_diag_qq.png,
     07_diag_resid_by_year.png, 07_diag_resid_by_district.png, 07_diag_leave_one_district_out.png. -->

## 13. The 100 mm deficit and weak-monsoon scenarios
<!-- src/08_scenario_100mm.py -> outputs/final/tables/08_scenario_results.csv, 08_scenario_range_curve.csv;
     figures 08_scenario_range_curve.png, 08_scenario_district_effects.png. Weak-monsoon rows are ILLUSTRATIVE;
     timing models: proportional split = main timing scenario, single windows = sensitivity, timing_quad = exploratory. -->

## 14. Robustness checks
<!-- src/09_robustness.py -> outputs/final/tables/09_robust_results.csv, 09_robust_skipped.csv; figure 09_robust_forest.png
     (small-area rows, area weights, wider district set, trend variants incl. year FE, rainfall windows, drought years). -->

## 15. Discussion and limitations
<!-- Draws on 07 diagnostics and 09 robustness; docs/HANDOFF.md data issues; no temperature in the prototype; old district
     boundaries; few year clusters; associations, not causal effects. -->

## 16. Conclusion
<!-- Summary of sections 10-14. No new numbers. -->

## References
<!-- Unnumbered back matter. -->
