# Viva preparation

Moved from docs/PROJECT_GUIDE.md (Part 10) on 2026-10-24, unchanged. Concepts and file references are explained in docs/PROJECT_GUIDE.md.

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
