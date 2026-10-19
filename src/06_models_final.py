"""Step 6: headline fixed-effects models in R_season (linear, quadratic) + robustness outcome (kg/ha).

Usage: python src/06_models_final.py <panel.csv> <outdir>
  prototype: python src/06_models_final.py data/processed/panel_v1.csv outputs/prototype
  final    : python src/06_models_final.py data/processed/panel_final.csv outputs/final

Model: y_dt = a_d + g*t + f(R_season_dt) + e_dt, PanelOLS entity effects, primary common linear trend
(SPEC A6). Outcomes: ln_yield (headline), yield_kgha (robustness).

Inference (SPEC A7): moving-block bootstrap over years (headline; L = BLOCK_LENGTH, sensitivity
BLOCK_LENGTH_SENSITIVITY; N_BOOT_BLOCK reps; seeds config.BOOT_SEEDS; full model refitted each rep),
side by side with district-clustered (+ wild cluster bootstrap), year-clustered, two-way clustered and
Driscoll-Kraay SEs (Bartlett, maxlags DK_MAXLAGS; unreliable with few years).
Linear vs quadratic verdict: the squared-term test must agree at ALPHA across district CR, wild cluster
bootstrap, year CR, two-way CR, Driscoll-Kraay and MBB L = BLOCK_LENGTH; otherwise INCONCLUSIVE.
Headline model (SPEC A11.1, pre-specified): INCONCLUSIVE or LINEAR ADEQUATE -> linear (quadratic as
sensitivity, report the range across both if INCONCLUSIVE); QUADRATIC SUPPORTED -> quadratic.

Also: within R2, AIC/BIC (formula in pipeline_utils.gaussian_ic), classical F, leave-one-year-out
(LOYO) prediction error; log models converted to kg/ha with and without Duan smearing (SPEC A9).
Writes <outdir>/tables/06_models_*.csv and <outdir>/logs/06_models.txt.
"""
import numpy as np
import pandas as pd
from scipy import stats

import pipeline_utils as U
import config as C  # noqa: E402

HEADLINE = ["linear", "quadratic", "linear_level", "quadratic_level"]
VERDICT_METHODS = ["district_CR", "wild_district", "year_CR", "twoway_CR", "driscoll_kraay",
                   f"MBB_L{C.BLOCK_LENGTH}"]


def loyo(p: pd.DataFrame, outcome: str, rain: dict) -> pd.DataFrame:
    """Leave one year out: fit LSDV on the other years, predict the held-out year.
    ln models: kg/ha prediction naive = exp(pred); smeared = exp(pred) x mean(exp(training residuals))."""
    rows = []
    for y in sorted(p.year.unique()):
        tr, te = p[p.year != y], p[p.year == y]
        pred, res_tr = U.lsdv_fit_predict(tr, te, outcome, rain)
        obs = te.yield_kgha.to_numpy()
        r = {"year": y, "n": len(te)}
        if outcome == "ln_yield":
            smear = float(np.mean(np.exp(res_tr)))
            naive, smeared = np.exp(pred), smear * np.exp(pred)
            r.update({"smear_factor": smear, "sse_ln": float(np.sum((te.ln_yield.to_numpy() - pred) ** 2)),
                      "sse_kgha_naive": float(np.sum((obs - naive) ** 2)),
                      "sse_kgha_smeared": float(np.sum((obs - smeared) ** 2)),
                      "sae_kgha_naive": float(np.sum(np.abs(obs - naive))),
                      "sae_kgha_smeared": float(np.sum(np.abs(obs - smeared)))})
        else:
            r.update({"smear_factor": np.nan, "sse_ln": np.nan,
                      "sse_kgha_naive": float(np.sum((obs - pred) ** 2)), "sse_kgha_smeared": np.nan,
                      "sae_kgha_naive": float(np.sum(np.abs(obs - pred))), "sae_kgha_smeared": np.nan})
        rows.append(r)
    return pd.DataFrame(rows)


def mbb_params(p: pd.DataFrame, specs: dict) -> dict:
    """{(model, L): (B, k) array of bootstrap coefficients}, same draws for every model."""
    years, yrows = U.year_rows(p)
    out = {}
    for L in [C.BLOCK_LENGTH] + list(C.BLOCK_LENGTH_SENSITIVITY):
        draws = U.block_draws(len(years), L, C.N_BOOT_BLOCK, C.BOOT_SEEDS[f"block_L{L}"])
        fes = {m: U.FastFE(p, s["outcome"], s["rain"]) for m, s in specs.items()}
        acc = {m: [] for m in specs}
        for dr in draws:
            rows = U.rows_from_year_draw(yrows, dr)
            for m, fe in fes.items():
                acc[m].append(fe.fit(rows))
        for m in specs:
            out[(m, L)] = (fes[m].cols, np.array(acc[m]))
    return out


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "06_models", a.panel)
    p = U.load_panel(a.panel)
    T = p.year.nunique()
    out.log(f"Panel: {U.describe_panel(p)}")
    out.log("Estimator: PanelOLS, entity (district) effects + common linear trend (t = year - 2000).")
    out.log(f"Headline intervals: moving-block bootstrap over years, L = {C.BLOCK_LENGTH} "
            f"(sensitivity {C.BLOCK_LENGTH_SENSITIVITY}), {C.N_BOOT_BLOCK} reps, seeds "
            + ", ".join(f"L{L}={C.BOOT_SEEDS[f'block_L{L}']}" for L in [C.BLOCK_LENGTH] + C.BLOCK_LENGTH_SENSITIVITY)
            + "; whole years with all districts; district effects, trend and rainfall terms refitted each rep.")
    out.log(f"Driscoll-Kraay: Bartlett kernel, lags 0..{C.DK_MAXLAGS}. FLAG: unreliable with T = {T} years.")
    out.log("AIC/BIC: llf = -n/2 [ln(2 pi) + ln(SSR/n) + 1]; AIC = -2 llf + 2k; BIC = -2 llf + k ln(n);")
    out.log("k = slope parameters + number of district effects. Compare AIC/BIC only within the same outcome.\n")

    specs = {k: U.MODELS[k] for k in HEADLINE}
    refs = {"trend_only": {"outcome": "ln_yield", "rain": {}, "role": "reference (no rainfall)"},
            "trend_only_level": {"outcome": "yield_kgha", "rain": {}, "role": "reference (no rainfall)"}}
    boot = mbb_params(p, specs)

    coef_rows, se_rows, fit_rows, loyo_rows, verdict_rows = [], [], [], [], []
    ssr = {}
    for name, s in {**specs, **refs}.items():
        res = U.fit_fe(p, s["outcome"], s["rain"])
        n, n_ent = int(res.nobs), int(res.entity_info["total"])
        k = len(res.params) + n_ent
        ic = U.gaussian_ic(float(res.resid_ss), n, k)
        ssr[name] = float(res.resid_ss)
        out.log("-" * 100)
        out.log(f"MODEL {name}  [{s['role']}]  outcome={s['outcome']}  regressors={list(res.params.index)}")
        out.log("-" * 100)
        out.log(f"within R2 = {res.rsquared_within:.4f}  N = {n}  districts = {n_ent}  SSR = {res.resid_ss:.6g}  "
                f"k = {k}  llf = {ic['llf']:.3f}  AIC = {ic['aic']:.3f}  BIC = {ic['bic']:.3f}")
        frow = {"model": name, "role": s["role"], "outcome": s["outcome"], "n": n, "districts": n_ent,
                "within_r2": res.rsquared_within, "ssr": res.resid_ss, **ic}

        # Coefficients with every SE method side by side.
        fits = {cov: U.fit_fe(p, s["outcome"], s["rain"], cov=cov) for cov in U.COV_METHODS}
        for term in res.params.index:
            base = {"model": name, "role": s["role"], "outcome": s["outcome"], "term": term, "coef": res.params[term]}
            coef_rows.append({**base, "se_year_CR": res.std_errors[term], "p_year_CR": res.pvalues[term]})
            for cov, r in fits.items():
                se_rows.append({**base, "method": cov, "se": r.std_errors[term], "p": r.pvalues[term],
                                "ci_lo": r.params[term] - 1.96 * r.std_errors[term],
                                "ci_hi": r.params[term] + 1.96 * r.std_errors[term],
                                "flag": f"unreliable with T={T}" if cov == "driscoll_kraay" else ""})
            if name in specs:
                if term != "trend":
                    w = U.wild_cluster_test(p, s["outcome"], s["rain"], term)
                    se_rows.append({**base, "method": "wild_district", "se": np.nan, "p": w["p"], "ci_lo": np.nan,
                                    "ci_hi": np.nan, "flag": f"WCR bootstrap-t, {w['draws']}"})
                for L in [C.BLOCK_LENGTH] + list(C.BLOCK_LENGTH_SENSITIVITY):
                    cols, arr = boot[(name, L)]
                    bs = U.boot_summary(arr[:, cols.index(term)], res.params[term])
                    se_rows.append({**base, "method": f"MBB_L{L}", "se": bs["se"], "p": bs["p"], "ci_lo": bs["lo"],
                                    "ci_hi": bs["hi"], "flag": ("headline" if L == C.BLOCK_LENGTH else "sensitivity")
                                    + f"; percentile CI and p; {bs['n']} reps"})
        se_df = pd.DataFrame([r for r in se_rows if r["model"] == name])
        piv = se_df.pivot(index="term", columns="method", values="se").reindex(index=list(res.params.index))
        pivp = se_df.pivot(index="term", columns="method", values="p").reindex(index=list(res.params.index))
        out.log("coef:  " + "  ".join(f"{t} = {res.params[t]:.6g}" for t in res.params.index))
        out.log("SE by method:")
        out.log(piv.to_string(float_format=lambda x: f"{x:.4g}"))
        out.log("p-value by method (H0: coef = 0):")
        out.log(pivp.to_string(float_format=lambda x: f"{x:.4f}"))

        sq = [c for c in res.params.index if c.endswith("_sq")]
        if sq:
            w = res.wald_test(formula=[f"{c} = 0" for c in sq])
            q = len(sq)
            f_cl = w.stat / q
            p_f_cl = stats.f.sf(f_cl, q, T - 1)
            lin = name.replace("quadratic", "linear")
            dfd = n - k
            f_classic = ((ssr[lin] - ssr[name]) / q) / (ssr[name] / dfd)
            p_classic = stats.f.sf(f_classic, q, dfd)
            out.log(f"Squared term ({sq[0]} = 0): year-CR Wald chi2(1) = {w.stat:.4f}, F = {f_cl:.4f}, "
                    f"p[F(1,{T - 1})] = {p_f_cl:.4f}; classical F = {f_classic:.4f}, p[F(1,{dfd})] = {p_classic:.4f} "
                    "(iid errors; not in verdict)")
            frow.update({"sq_F_yearCR": f_cl, "sq_F_yearCR_p": p_f_cl, "sq_F_classic": f_classic,
                         "sq_F_classic_p": p_classic})
            vp = {m: float(pivp.loc[sq[0], m]) for m in VERDICT_METHODS}
            sig = {m: v < C.ALPHA for m, v in vp.items()}
            verdict = ("QUADRATIC SUPPORTED (squared term significant under every method)" if all(sig.values())
                       else "LINEAR ADEQUATE (squared term not significant under any method)" if not any(sig.values())
                       else "INCONCLUSIVE (methods disagree)")
            sens = {f"MBB_L{L}": float(pivp.loc[sq[0], f"MBB_L{L}"]) for L in C.BLOCK_LENGTH_SENSITIVITY}
            out.log(f"LINEAR vs QUADRATIC at alpha = {C.ALPHA}: {verdict}")
            out.log("  p by method: " + ", ".join(f"{m} {v:.4f}{'*' if sig[m] else ''}" for m, v in vp.items())
                    + "   (* = significant)")
            out.log("  sensitivity (not in verdict): " + ", ".join(f"{m} {v:.4f}" for m, v in sens.items()))
            # Pre-specified headline rule (SPEC A11.1), fixed before any gridded result.
            lin = name.replace("quadratic", "linear")
            headline = name if verdict.startswith("QUADRATIC") else lin
            sensitivity = lin if headline == name else name
            out.log(f"  HEADLINE (SPEC A11.1): {headline}; sensitivity: {sensitivity}"
                    + ("; report the range across both" if verdict.startswith("INCONCLUSIVE") else ""))
            verdict_rows.append({"model": name, "term": sq[0], "verdict": verdict, "headline_model": headline,
                                 "sensitivity_model": sensitivity,
                                 "report_range_across_both": verdict.startswith("INCONCLUSIVE"), **{f"p_{m}": v for m, v in vp.items()},
                                 **{f"p_{m}_sensitivity": v for m, v in sens.items()}, "p_classical_F": p_classic,
                                 "aic_linear": None, "aic_quadratic": ic["aic"]})
            v = list(s["rain"])[0]
            b1, b2 = res.params[v], res.params[f"{v}_sq"]
            frow["turning_point_mm"] = -b1 / (2 * b2)
            out.log(f"  turning point -b1/(2 b2) = {frow['turning_point_mm']:.1f} mm ({'max' if b2 < 0 else 'min'}); "
                    f"observed {p[v].min():.1f}-{p[v].max():.1f} mm")

        lo = loyo(p, s["outcome"], s["rain"])
        ntot = lo.n.sum()
        frow["loyo_rmse_ln"] = np.sqrt(lo.sse_ln.sum() / ntot) if s["outcome"] == "ln_yield" else np.nan
        frow["loyo_rmse_kgha_naive"] = np.sqrt(lo.sse_kgha_naive.sum() / ntot)
        frow["loyo_rmse_kgha_smeared"] = np.sqrt(lo.sse_kgha_smeared.sum() / ntot) if s["outcome"] == "ln_yield" else np.nan
        frow["loyo_mae_kgha_naive"] = lo.sae_kgha_naive.sum() / ntot
        frow["loyo_mae_kgha_smeared"] = lo.sae_kgha_smeared.sum() / ntot if s["outcome"] == "ln_yield" else np.nan
        frow["mean_smear_factor"] = lo.smear_factor.mean()
        out.log(f"LOYO: RMSE ln = {frow['loyo_rmse_ln']:.4f}; RMSE kg/ha naive = {frow['loyo_rmse_kgha_naive']:.1f}, "
                f"smeared = {frow['loyo_rmse_kgha_smeared']:.1f} (mean Duan factor {frow['mean_smear_factor']:.4f})")
        lo["model"] = name
        lo["rmse_kgha_naive_year"] = np.sqrt(lo.sse_kgha_naive / lo.n)
        lo["rmse_kgha_smeared_year"] = np.sqrt(lo.sse_kgha_smeared / lo.n)
        loyo_rows.append(lo)
        fit_rows.append(frow)
        out.log("")

    fits = pd.DataFrame(fit_rows)
    for r in verdict_rows:
        r["aic_linear"] = float(fits.set_index("model").aic[r["model"].replace("quadratic", "linear")])
    out.log("=" * 100)
    out.log("MODEL COMPARISON (AIC/BIC comparable only within the same outcome)")
    show = ["model", "outcome", "within_r2", "aic", "bic", "loyo_rmse_ln", "loyo_rmse_kgha_naive",
            "loyo_rmse_kgha_smeared", "loyo_mae_kgha_naive", "loyo_mae_kgha_smeared"]
    out.log(fits[show].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    out.log("\nHeld-out comparison in kg/ha (SPEC A9): log models vs trend-only, naive vs Duan-smeared:")
    f_ = fits.set_index("model")
    for m in ["linear", "quadratic"]:
        for kind in ["naive", "smeared"]:
            d = f_.loc[m, f"loyo_rmse_kgha_{kind}"] - f_.loc["trend_only", f"loyo_rmse_kgha_{kind}"]
            out.log(f"  {m:9s} {kind:7s}: RMSE {f_.loc[m, f'loyo_rmse_kgha_{kind}']:.1f} vs trend-only "
                    f"{f_.loc['trend_only', f'loyo_rmse_kgha_{kind}']:.1f} -> "
                    f"{'better' if d < 0 else 'worse'} by {abs(d):.1f} kg/ha")
    out.log(f"  level models (no back-transform): linear_level {f_.loc['linear_level', 'loyo_rmse_kgha_naive']:.1f}, "
            f"quadratic_level {f_.loc['quadratic_level', 'loyo_rmse_kgha_naive']:.1f}, trend_only_level "
            f"{f_.loc['trend_only_level', 'loyo_rmse_kgha_naive']:.1f}")
    out.log("\nLINEAR vs QUADRATIC VERDICTS")
    vd = pd.DataFrame(verdict_rows)
    for r in vd.itertuples():
        out.log(f"  {r.model}: {r.verdict} -> headline {r.headline_model} (SPEC A11.1)")
    ly = pd.concat(loyo_rows)
    out.log("\nLOYO RMSE by held-out year (kg/ha, ln models smeared):")
    ly["rmse_kgha_year"] = np.where(ly.sse_ln.notna(), ly.rmse_kgha_smeared_year, ly.rmse_kgha_naive_year)
    out.log(ly.pivot(index="year", columns="model", values="rmse_kgha_year").round(1).to_string())

    for df, nm in [(pd.DataFrame(coef_rows), "coefficients"), (pd.DataFrame(se_rows), "se_comparison"),
                   (fits, "fit_stats"), (vd, "linear_vs_quadratic"), (ly, "loyo_by_year")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")
    out.log("Results are associations under the model's assumptions; fixed effects remove only time-invariant "
            "district confounders.")
    out.close()


if __name__ == "__main__":
    main()
