"""Step 6: final fixed-effects models (SPEC A13.2) with the A7 inference set and the A11.1 headline rule.

Usage: python src/06_models_final.py <panel.csv> <outdir>
  final: python src/06_models_final.py data/processed/panel_final.csv outputs/final

Models: ln(yield) = a_d + g*t + weather terms + e (PanelOLS district effects, common linear trend).
  M1 (headline, linear)    : Rc, Tc
  M2 (headline, quadratic) : Rc, Rc^2, Tc, Tc^2
  Rc = (R_season - grand mean)/100 (per 100 mm), Tc = T_season - grand mean (per deg C).
  Exploratory: timing (Rec, Rlc, dry_spell_max, Tc); M2_rain_only (Rc, Rc^2, Tc).
  Robustness outcome: M1_level, M2_level (yield in kg/ha). References: trend-only models.
Inference (A7): moving-block bootstrap over years (headline, L = BLOCK_LENGTH; sensitivity
BLOCK_LENGTH_SENSITIVITY; N_BOOT_BLOCK reps; seeds config.BOOT_SEEDS), district-, year- and two-way
clustered SEs, Driscoll-Kraay (Bartlett, lags 0..DK_MAXLAGS; flagged unreliable with few years), wild
cluster bootstrap by district (WCR, exact enumeration).
Linear vs quadratic (A13.2): joint test of Rc^2 and Tc^2 = 0 (q = 2) under district CR, wild bootstrap,
year CR, two-way CR, Driscoll-Kraay and MBB L = BLOCK_LENGTH (bootstrap-covariance Wald). Same verdict at
ALPHA under all -> QUADRATIC SUPPORTED or LINEAR ADEQUATE; otherwise INCONCLUSIVE.
Headline rule (A11.1, pre-specified): INCONCLUSIVE or LINEAR ADEQUATE -> M1 headline (M2 as sensitivity,
range reported if INCONCLUSIVE); QUADRATIC SUPPORTED -> M2.
Also: within R2, AIC/BIC (pipeline_utils.gaussian_ic), leave-one-year-out prediction (log models to kg/ha
naive and Duan-smeared, A9), and the trend re-examination with 2016-2017 (A13.4e).
"""
import numpy as np
import pandas as pd
from scipy import stats

import pipeline_utils as U
import config as C  # noqa: E402

FITTED = ["M1", "M2", "M1_level", "M2_level", "timing", "M2_rain_only"]
PAIRS = [("M1", "M2"), ("M1_level", "M2_level")]
VERDICT_METHODS = ["district_CR", "wild_district", "year_CR", "twoway_CR", "driscoll_kraay", f"MBB_L{C.BLOCK_LENGTH}"]
LS = [C.BLOCK_LENGTH] + list(C.BLOCK_LENGTH_SENSITIVITY)


def loyo(p: pd.DataFrame, outcome: str, rain: dict) -> pd.DataFrame:
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
                      "sse_kgha_naive": float(np.sum((obs - naive) ** 2)), "sse_kgha_smeared": float(np.sum((obs - smeared) ** 2))})
        else:
            r.update({"smear_factor": np.nan, "sse_ln": np.nan, "sse_kgha_naive": float(np.sum((obs - pred) ** 2)),
                      "sse_kgha_smeared": np.nan})
        rows.append(r)
    return pd.DataFrame(rows)


def mbb(p: pd.DataFrame, specs: dict) -> dict:
    years, yrows = U.year_rows(p)
    out = {}
    fes = {m: U.FastFE(p, s["outcome"], s["rain"]) for m, s in specs.items()}
    for L in LS:
        draws = U.block_draws(len(years), L, C.N_BOOT_BLOCK, C.BOOT_SEEDS[f"block_L{L}"])
        acc = {m: [] for m in specs}
        for dr in draws:
            rows = U.rows_from_year_draw(yrows, dr)
            for m, fe in fes.items():
                acc[m].append(fe.fit(rows))
        for m in specs:
            out[(m, L)] = pd.DataFrame(np.array(acc[m]), columns=fes[m].cols)
    return out


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "06_models", a.panel)
    p = U.load_panel(a.panel)
    c = p.attrs["consts"]
    T = p.year.nunique()
    out.log(f"Panel: {U.describe_panel(p)}")
    out.log(f"Centring (grand means): R_season {c['R_season']:.2f} mm, T_season {c['T_season']:.4f} deg C. "
            f"Rc in units of {C.RAIN_UNIT_MM:g} mm; Tc in deg C. Coefficients are per 100 mm and per 1 deg C "
            "(in quadratic models: marginal effect at the grand mean).")
    out.log(f"MBB: L = {C.BLOCK_LENGTH} (headline), {C.BLOCK_LENGTH_SENSITIVITY} (sensitivity), {C.N_BOOT_BLOCK} reps, "
            "seeds " + ", ".join(f"L{L}={C.BOOT_SEEDS[f'block_L{L}']}" for L in LS) + "; full model refitted each rep.")
    out.log(f"Driscoll-Kraay: Bartlett, lags 0..{C.DK_MAXLAGS}. FLAG: unreliable with T = {T} years.")
    out.log("AIC/BIC: llf = -n/2 [ln(2 pi) + ln(SSR/n) + 1]; AIC = -2 llf + 2k; BIC = -2 llf + k ln(n); k = slopes + "
            "district effects; compare only within the same outcome.\n")
    pd.DataFrame([c]).pipe(lambda d: out.table(d, "centring_constants"))

    specs = {m: U.MODELS[m] for m in FITTED}
    refs = {"trend_only": {"outcome": "ln_yield", "rain": {}, "role": "reference (no weather)"},
            "trend_only_level": {"outcome": "yield_kgha", "rain": {}, "role": "reference (no weather)"}}
    boot = mbb(p, specs)
    coef_rows, se_rows, fit_rows, loyo_rows, verdict_rows = [], [], [], [], []
    res_all = {}
    for name, s in {**specs, **refs}.items():
        res = U.fit_fe(p, s["outcome"], s["rain"])
        res_all[name] = res
        n, n_ent = int(res.nobs), int(res.entity_info["total"])
        k = len(res.params) + n_ent
        ic = U.gaussian_ic(float(res.resid_ss), n, k)
        out.log("-" * 100)
        out.log(f"MODEL {name}  [{s['role']}]  outcome={s['outcome']}  regressors={list(res.params.index)}")
        out.log("-" * 100)
        out.log(f"within R2 = {res.rsquared_within:.4f}  N = {n}  districts = {n_ent}  k = {k}  AIC = {ic['aic']:.3f}  "
                f"BIC = {ic['bic']:.3f}")
        frow = {"model": name, "role": s["role"], "outcome": s["outcome"], "n": n, "within_r2": res.rsquared_within,
                "ssr": float(res.resid_ss), **ic}
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
                    w = U.wild_cluster_wald(p, s["outcome"], s["rain"], [term])
                    se_rows.append({**base, "method": "wild_district", "se": np.nan, "p": w["p"], "ci_lo": np.nan,
                                    "ci_hi": np.nan, "flag": f"WCR, {w['draws']}"})
                for L in LS:
                    bs = U.boot_summary(boot[(name, L)][term].to_numpy(), res.params[term])
                    se_rows.append({**base, "method": f"MBB_L{L}", "se": bs["se"], "p": bs["p"], "ci_lo": bs["lo"],
                                    "ci_hi": bs["hi"], "flag": ("headline" if L == C.BLOCK_LENGTH else "sensitivity")
                                    + f"; percentile CI/p; {bs['n']} reps"})
        sd = pd.DataFrame([r for r in se_rows if r["model"] == name])
        idx = list(res.params.index)
        out.log("coef: " + "  ".join(f"{t} = {res.params[t]:.5g}" for t in idx))
        out.log("SE by method:\n" + sd.pivot(index="term", columns="method", values="se").reindex(idx)
                .to_string(float_format=lambda x: f"{x:.4g}"))
        out.log("p by method:\n" + sd.pivot(index="term", columns="method", values="p").reindex(idx)
                .to_string(float_format=lambda x: f"{x:.4f}"))
        mb = sd[sd.method == f"MBB_L{C.BLOCK_LENGTH}"]
        if len(mb):
            out.log(f"MBB L{C.BLOCK_LENGTH} 95% CI: " + "; ".join(f"{r.term} [{r.ci_lo:.4g}, {r.ci_hi:.4g}]"
                                                                for r in mb.itertuples()))
        for v in ["Rc", "Tc"]:
            if f"{v}_sq" in res.params.index:
                tp = -res.params[v] / (2 * res.params[f"{v}_sq"])
                raw = c["R_season"] + C.RAIN_UNIT_MM * tp if v == "Rc" else c["T_season"] + tp
                obs = (p.R_season.min(), p.R_season.max()) if v == "Rc" else (p.T_season.min(), p.T_season.max())
                frow[f"turning_point_{v}"] = raw
                out.log(f"  turning point of {v}: {raw:.2f} {'mm' if v == 'Rc' else 'deg C'} "
                        f"({'max' if res.params[f'{v}_sq'] < 0 else 'min'}); observed {obs[0]:.2f}-{obs[1]:.2f}")
        lo = loyo(p, s["outcome"], s["rain"])
        nt = lo.n.sum()
        frow.update({"loyo_rmse_ln": np.sqrt(lo.sse_ln.sum() / nt) if s["outcome"] == "ln_yield" else np.nan,
                     "loyo_rmse_kgha_naive": np.sqrt(lo.sse_kgha_naive.sum() / nt),
                     "loyo_rmse_kgha_smeared": np.sqrt(lo.sse_kgha_smeared.sum() / nt) if s["outcome"] == "ln_yield" else np.nan,
                     "mean_smear_factor": lo.smear_factor.mean()})
        out.log(f"LOYO: RMSE ln = {frow['loyo_rmse_ln']:.4f}; kg/ha naive {frow['loyo_rmse_kgha_naive']:.1f}, "
                f"smeared {frow['loyo_rmse_kgha_smeared']:.1f}\n")
        lo["model"] = name
        loyo_rows.append(lo)
        fit_rows.append(frow)

    # ---- Linear vs quadratic verdicts and the headline rule ----
    out.log("=" * 100)
    out.log("LINEAR vs QUADRATIC (joint test Rc^2 = Tc^2 = 0, q = 2)")
    for lin, quad in PAIRS:
        s = specs[quad]
        sq = ["Rc_sq", "Tc_sq"]
        pv = {}
        for cov in ["district_CR", "year_CR", "twoway_CR", "driscoll_kraay"]:
            pv[cov] = float(U.fit_fe(p, s["outcome"], s["rain"], cov=cov).wald_test(formula=[f"{t} = 0" for t in sq]).pval)
        pv["wild_district"] = U.wild_cluster_wald(p, s["outcome"], s["rain"], sq)["p"]
        for L in LS:
            pv[f"MBB_L{L}"] = U.boot_wald(boot[(quad, L)][sq].to_numpy(), res_all[quad].params[sq].to_numpy())["p"]
        sig = {m: pv[m] < C.ALPHA for m in VERDICT_METHODS}
        verdict = ("QUADRATIC SUPPORTED (squared terms significant under every method)" if all(sig.values())
                   else "LINEAR ADEQUATE (squared terms not significant under any method)" if not any(sig.values())
                   else "INCONCLUSIVE (methods disagree)")
        headline = quad if verdict.startswith("QUADRATIC") else lin
        sens = lin if headline == quad else quad
        ssr_r, ssr_u = res_all[lin].resid_ss, res_all[quad].resid_ss
        k_u = len(res_all[quad].params) + int(res_all[quad].entity_info["total"])
        fcl = ((ssr_r - ssr_u) / 2) / (ssr_u / (len(p) - k_u))
        pcl = float(stats.f.sf(fcl, 2, len(p) - k_u))
        out.log(f"[{lin} vs {quad}] {verdict}")
        out.log("  p: " + ", ".join(f"{m} {pv[m]:.4f}{'*' if sig[m] else ''}" for m in VERDICT_METHODS)
                + f"   sensitivity: " + ", ".join(f"MBB_L{L} {pv[f'MBB_L{L}']:.4f}" for L in C.BLOCK_LENGTH_SENSITIVITY)
                + f"; classical F(2,{len(p) - k_u}) = {fcl:.3f}, p = {pcl:.4f} (iid; not in verdict)")
        out.log(f"  HEADLINE (A11.1): {headline}; sensitivity: {sens}"
                + ("; report the range across both" if verdict.startswith("INCONCLUSIVE") else ""))
        verdict_rows.append({"linear_model": lin, "quadratic_model": quad, "verdict": verdict, "headline_model": headline,
                             "sensitivity_model": sens, "report_range_across_both": verdict.startswith("INCONCLUSIVE"),
                             **{f"p_{m}": pv[m] for m in pv}, "p_classical_F": pcl,
                             "aic_linear": float(U.gaussian_ic(ssr_r, len(p), len(res_all[lin].params) + int(res_all[lin].entity_info["total"]))["aic"]),
                             "aic_quadratic": float(U.gaussian_ic(ssr_u, len(p), k_u)["aic"])})
    vd = pd.DataFrame(verdict_rows)

    # ---- Trend re-examination (A13.4e) ----
    out.log("\nTREND (A13.4e): coefficient on t = year - 2000, ln points per year")
    tr = []
    for nm, sub in [(f"{p.year.min()}-{p.year.max()}", p), (f"{p.year.min()}-2015", p[p.year <= 2015])]:
        for m in ["trend_only", "M1", "M2"]:
            s = {**specs, **refs}[m]
            r = U.fit_fe(sub, s["outcome"], s["rain"])
            tr.append({"years": nm, "model": m, "trend": r.params["trend"], "se_year_CR": r.std_errors["trend"],
                       "p_year_CR": r.pvalues["trend"], "pct_per_year": 100 * (np.exp(r.params["trend"]) - 1)})
    tr = pd.DataFrame(tr)
    for m in ["M1", "M2"]:
        bs = U.boot_summary(boot[(m, C.BLOCK_LENGTH)]["trend"].to_numpy(), res_all[m].params["trend"])
        tr.loc[(tr.model == m) & (tr.years == tr.years.iat[0]), ["mbb_ci_lo", "mbb_ci_hi", "mbb_p"]] = [bs["lo"], bs["hi"], bs["p"]]
    out.log(tr.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    fits = pd.DataFrame(fit_rows)
    f_ = fits.set_index("model")
    out.log("\nMODEL COMPARISON")
    out.log(fits[["model", "outcome", "within_r2", "aic", "bic", "loyo_rmse_ln", "loyo_rmse_kgha_naive",
                  "loyo_rmse_kgha_smeared"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    out.log("Held-out (LOYO) kg/ha vs trend-only (A9):")
    for m in ["M1", "M2"]:
        for kind in ["naive", "smeared"]:
            d = f_.loc[m, f"loyo_rmse_kgha_{kind}"] - f_.loc["trend_only", f"loyo_rmse_kgha_{kind}"]
            out.log(f"  {m} {kind:7s}: {f_.loc[m, f'loyo_rmse_kgha_{kind}']:.1f} vs {f_.loc['trend_only', f'loyo_rmse_kgha_{kind}']:.1f}"
                    f" -> {'better' if d < 0 else 'worse'} by {abs(d):.1f}")
    out.log(f"  levels: M1_level {f_.loc['M1_level', 'loyo_rmse_kgha_naive']:.1f}, M2_level "
            f"{f_.loc['M2_level', 'loyo_rmse_kgha_naive']:.1f}, trend_only_level {f_.loc['trend_only_level', 'loyo_rmse_kgha_naive']:.1f}")
    out.log(f"  ln units: M1 {f_.loc['M1', 'loyo_rmse_ln']:.4f}, M2 {f_.loc['M2', 'loyo_rmse_ln']:.4f}, trend_only "
            f"{f_.loc['trend_only', 'loyo_rmse_ln']:.4f}")
    ly = pd.concat(loyo_rows)
    for df, nm in [(pd.DataFrame(coef_rows), "coefficients"), (pd.DataFrame(se_rows), "se_comparison"),
                   (fits, "fit_stats"), (vd, "linear_vs_quadratic"), (ly, "loyo_by_year"), (tr, "trend")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")
    out.log("Results are associations under the model's assumptions; fixed effects remove only time-invariant "
            "district confounders.")
    out.close()


if __name__ == "__main__":
    main()
