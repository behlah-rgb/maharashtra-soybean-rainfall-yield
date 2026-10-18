"""Step 6: headline fixed-effects models in R_season (linear, quadratic) + robustness outcome (kg/ha).

Usage: python src/06_models_final.py <panel.csv> <outdir>
  prototype: python src/06_models_final.py data/processed/panel_v1.csv outputs/prototype
  final    : python src/06_models_final.py data/processed/panel_final.csv outputs/final

Model: y_dt = a_d + g*t + f(R_season_dt) + e_dt, PanelOLS entity effects, primary common linear trend
(SPEC A6), SEs clustered by year. Outcomes: ln_yield (headline), yield_kgha (robustness).
Reports coefficients, within R2, F-test on the squared term (clustered Wald and classical F),
AIC/BIC (formula in pipeline_utils.gaussian_ic), leave-one-year-out (LOYO) prediction error.
Writes <outdir>/tables/06_models_*.csv and <outdir>/logs/06_models.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats

import pipeline_utils as U

HEADLINE = ["linear", "quadratic", "linear_level", "quadratic_level"]


def loyo(p: pd.DataFrame, outcome: str, rain: dict) -> pd.DataFrame:
    """Leave one year out: fit LSDV on the other years, predict the held-out year."""
    rows = []
    for y in sorted(p.year.unique()):
        tr, te = p[p.year != y], p[p.year == y]
        pred, res_tr = U.lsdv_fit_predict(tr, te, outcome, rain)
        r = {"year": y, "n": len(te)}
        if outcome == "ln_yield":
            smear = np.mean(np.exp(res_tr))  # Duan smearing factor for exp back-transform
            r["sse_ln"] = float(np.sum((te.ln_yield.to_numpy() - pred) ** 2))
            r["sse_kgha"] = float(np.sum((te.yield_kgha.to_numpy() - smear * np.exp(pred)) ** 2))
            r["sae_kgha"] = float(np.sum(np.abs(te.yield_kgha.to_numpy() - smear * np.exp(pred))))
        else:
            r["sse_ln"] = np.nan
            r["sse_kgha"] = float(np.sum((te.yield_kgha.to_numpy() - pred) ** 2))
            r["sae_kgha"] = float(np.sum(np.abs(te.yield_kgha.to_numpy() - pred)))
        rows.append(r)
    return pd.DataFrame(rows)


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "06_models", a.panel)
    p = U.load_panel(a.panel)
    out.log(f"Panel: {U.describe_panel(p)}")
    out.log("Estimator: PanelOLS, entity (district) effects + common linear trend (t = year - 2000), "
            "SEs clustered by year.")
    n_clusters = p.year.nunique()
    out.log(f"Year clusters: {n_clusters}. Cluster-robust inference with few clusters is approximate.\n")
    out.log("AIC/BIC: llf = -n/2 [ln(2 pi) + ln(SSR/n) + 1]; AIC = -2 llf + 2k; BIC = -2 llf + k ln(n);")
    out.log("k = slope parameters + number of district effects. Compare AIC/BIC only between models with the")
    out.log("same outcome (ln vs kg/ha likelihoods are on different scales).\n")

    coef_rows, fit_rows, loyo_rows = [], [], []
    ssr = {}
    specs = {k: U.MODELS[k] for k in HEADLINE}
    # Trend-only baselines (no rainfall) as a reference for LOYO and IC.
    specs["trend_only"] = {"outcome": "ln_yield", "rain": {}, "role": "reference (no rainfall)"}
    specs["trend_only_level"] = {"outcome": "yield_kgha", "rain": {}, "role": "reference (no rainfall)"}

    for name, s in specs.items():
        res = U.fit_fe(p, s["outcome"], s["rain"])
        n, n_ent = int(res.nobs), int(res.entity_info["total"])
        k = len(res.params) + n_ent
        ic = U.gaussian_ic(float(res.resid_ss), n, k)
        ssr[name] = (float(res.resid_ss), n, k)
        out.log("-" * 92)
        out.log(f"MODEL {name}  [{s['role']}]  outcome={s['outcome']}  regressors={list(res.params.index)}")
        out.log("-" * 92)
        tab = pd.DataFrame({"coef": res.params, "se_cluster_year": res.std_errors, "t": res.tstats, "p": res.pvalues})
        out.log(tab.to_string(float_format=lambda x: f"{x:.6g}"))
        out.log(f"within R2 = {res.rsquared_within:.4f}  N = {n}  districts = {n_ent}  SSR = {res.resid_ss:.6g}  "
                f"k = {k}  llf = {ic['llf']:.3f}  AIC = {ic['aic']:.3f}  BIC = {ic['bic']:.3f}")
        for c in res.params.index:
            coef_rows.append({"model": name, "role": s["role"], "outcome": s["outcome"], "term": c,
                              "coef": res.params[c], "se_cluster_year": res.std_errors[c],
                              "t": res.tstats[c], "p": res.pvalues[c]})
        frow = {"model": name, "role": s["role"], "outcome": s["outcome"], "n": n, "districts": n_ent,
                "within_r2": res.rsquared_within, "ssr": res.resid_ss, **ic}

        sq = [c for c in res.params.index if c.endswith("_sq")]
        if sq:
            w = res.wald_test(formula=[f"{c} = 0" for c in sq])
            q = len(sq)
            f_cl = w.stat / q
            p_f_cl = stats.f.sf(f_cl, q, n_clusters - 1)
            lin = name.replace("quadratic", "linear")
            ssr_r, _, _ = ssr[lin]
            ssr_u = float(res.resid_ss)
            f_cl_dfd = n - k
            f_classic = ((ssr_r - ssr_u) / q) / (ssr_u / f_cl_dfd)
            p_classic = stats.f.sf(f_classic, q, f_cl_dfd)
            out.log(f"Squared term test ({', '.join(sq)} = 0):")
            out.log(f"  clustered Wald chi2({q}) = {w.stat:.4f}, p = {w.pval:.4f};  "
                    f"F = W/q = {f_cl:.4f}, p[F({q},{n_clusters - 1})] = {p_f_cl:.4f}")
            out.log(f"  classical F (SSR {lin} vs {name}) = {f_classic:.4f}, p[F({q},{f_cl_dfd})] = {p_classic:.4f}"
                    "  (assumes iid errors)")
            frow.update({"sq_wald_chi2": w.stat, "sq_wald_p": w.pval, "sq_F_cluster": f_cl,
                         "sq_F_cluster_p": p_f_cl, "sq_F_classic": f_classic, "sq_F_classic_p": p_classic})
            v = list(s["rain"])[0]
            b1, b2 = res.params[v], res.params[f"{v}_sq"]
            tp = -b1 / (2 * b2)
            frow["turning_point_mm"] = tp
            out.log(f"  turning point -b1/(2 b2) = {tp:.1f} mm ({'max' if b2 < 0 else 'min'}); "
                    f"observed {p[v].min():.1f}-{p[v].max():.1f} mm")

        lo = loyo(p, s["outcome"], s["rain"])
        ntot = lo.n.sum()
        frow["loyo_rmse_ln"] = np.sqrt(lo.sse_ln.sum() / ntot) if s["outcome"] == "ln_yield" else np.nan
        frow["loyo_rmse_kgha"] = np.sqrt(lo.sse_kgha.sum() / ntot)
        frow["loyo_mae_kgha"] = lo.sae_kgha.sum() / ntot
        out.log(f"LOYO: RMSE ln = {frow['loyo_rmse_ln']:.4f}  RMSE kg/ha = {frow['loyo_rmse_kgha']:.1f}  "
                f"MAE kg/ha = {frow['loyo_mae_kgha']:.1f}"
                + ("  (ln models: kg/ha via exp(pred) x Duan smearing factor)" if s["outcome"] == "ln_yield" else ""))
        lo["model"] = name
        lo["rmse_ln_year"] = np.sqrt(lo.sse_ln / lo.n)
        lo["rmse_kgha_year"] = np.sqrt(lo.sse_kgha / lo.n)
        loyo_rows.append(lo[["model", "year", "n", "rmse_ln_year", "rmse_kgha_year"]])
        fit_rows.append(frow)
        out.log("")

    fits = pd.DataFrame(fit_rows)
    out.log("=" * 92)
    out.log("MODEL COMPARISON (AIC/BIC comparable only within the same outcome)")
    show = ["model", "outcome", "within_r2", "aic", "bic", "loyo_rmse_ln", "loyo_rmse_kgha", "loyo_mae_kgha",
            "sq_F_cluster_p", "sq_F_classic_p"]
    out.log(fits[show].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    out.log("")
    out.log("LOYO RMSE by held-out year (kg/ha):")
    ly = pd.concat(loyo_rows)
    out.log(ly.pivot(index="year", columns="model", values="rmse_kgha_year").round(1).to_string())

    for df, nm in [(pd.DataFrame(coef_rows), "coefficients"), (fits, "fit_stats"), (ly, "loyo_by_year")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")
    out.log("Results are associations under the model's assumptions; fixed effects remove only time-invariant "
            "district confounders.")
    out.close()


if __name__ == "__main__":
    main()
