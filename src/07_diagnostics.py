"""Step 7: diagnostics for the headline models M1 (linear) and M2 (quadratic) in R and T (SPEC A13.2), ln yield.

Usage: python src/07_diagnostics.py <panel.csv> <outdir>

The fixed-effects model is re-estimated as LSDV (statsmodels OLS with district dummies + trend +
rainfall); slopes are asserted equal to PanelOLS. LSDV residuals = within residuals.

Outputs (<outdir>/figures, tables, logs; prefix 07_diag):
- residual vs fitted, Q-Q, residuals by year, residuals by district (figures)
- tests: Breusch-Pagan (heteroskedasticity on trend + rainfall terms), Brown-Forsythe/Levene
  (residual variance equal across districts / years), Jarque-Bera (normality),
  Wooldridge (2002) test for AR(1) serial correlation in panels (first-difference residuals,
  H0: corr = -0.5, district-clustered SE), Pesaran CD (cross-sectional dependence; added because
  districts share rainfall series)
- influence: leverage, studentized residuals, Cook's distance, DFBETAS for rainfall terms
- leave-one-district-out coefficient stability (table + figure); 100 mm effect at mean R with T at its mean
- multicollinearity between rainfall and temperature: within-district correlation of Rc and Tc, VIFs of the
  regressors on district-demeaned data, and the condition number of the demeaned design
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import OLSInfluence
from statsmodels.stats.stattools import jarque_bera

import pipeline_utils as U
import config as C

MODELS = ["M1", "M2"]


def lsdv(p: pd.DataFrame, rain: dict):
    D = pd.get_dummies(p.district, dtype=float)
    X = pd.concat([D, p[["trend"] + U.rain_terms(rain)]], axis=1)
    return sm.OLS(p.ln_yield, X).fit(), X


def wooldridge_ar1(p: pd.DataFrame, rain: dict) -> dict:
    """Wooldridge (2002, sec. 10.6.3) / Drukker (2003): regress first differences (Δtrend = 1 is the
    constant), take residuals u, regress u_t on u_{t-1}; under no serial correlation in e, coef = -0.5.
    SE clustered by district."""
    q = p.sort_values(["district", "year"]).copy()
    cols = ["ln_yield"] + U.rain_terms(rain)
    d = q.groupby("district")[cols].diff()
    d["district"], d["year"] = q.district, q.year
    d = d.dropna()
    fd = sm.OLS(d.ln_yield, sm.add_constant(d[U.rain_terms(rain)])).fit()
    d["u"] = fd.resid
    d["u_lag"] = d.groupby("district").u.shift(1)
    e = d.dropna(subset=["u_lag"])
    r = sm.OLS(e.u, e[["u_lag"]]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(e.district)[0]})
    b, se = r.params["u_lag"], r.bse["u_lag"]
    F = ((b + 0.5) / se) ** 2
    G = e.district.nunique()
    return {"coef_u_lag": b, "se_cluster_district": se, "F": F, "df1": 1, "df2": G - 1,
            "p": stats.f.sf(F, 1, G - 1)}


def pesaran_cd(p: pd.DataFrame, resid: pd.Series) -> dict:
    """Pesaran (2004) CD = sqrt(2T/(N(N-1))) * sum_{i<j} rho_ij, ~ N(0,1) under no cross-sectional dependence."""
    W = p.assign(e=resid.values).pivot(index="year", columns="district", values="e")
    R = W.corr().to_numpy()
    N, T = W.shape[1], W.shape[0]
    iu = np.triu_indices(N, 1)
    cd = np.sqrt(2 * T / (N * (N - 1))) * R[iu].sum()
    return {"CD": cd, "p": 2 * stats.norm.sf(abs(cd)), "mean_abs_rho": np.abs(R[iu]).mean(), "mean_rho": R[iu].mean()}


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "07_diag", a.panel)
    plt = U.setup_matplotlib()
    p = U.load_panel(a.panel)
    out.log(f"Panel: {U.describe_panel(p)}\n")
    order = [s for s in U.SUB_ORDER if s in set(p.subdivision)]
    dist_order = p.assign(o=p.subdivision.map({s: i for i, s in enumerate(order)})).sort_values(["o", "district"]).district.unique()

    fits, test_rows, infl_rows, lodo_rows = {}, [], [], []
    for name in MODELS:
        rain = U.MODELS[name]["rain"]
        res, X = lsdv(p, rain)
        po = U.fit_fe(p, "ln_yield", rain)
        for c in po.params.index:
            assert np.isclose(res.params[c], po.params[c], rtol=1e-8, atol=1e-12), f"LSDV != PanelOLS for {c}"
        fits[name] = res
        resid, fitted = res.resid, res.fittedvalues

        # Tests
        exog_het = sm.add_constant(p[["trend"] + U.rain_terms(rain)])
        lm, lm_p, fval, f_p = het_breuschpagan(resid, exog_het)
        test_rows.append({"model": name, "test": "Breusch-Pagan (resid^2 on trend + weather terms)",
                          "stat": lm, "p": lm_p, "note": f"LM; F version = {fval:.3f} (p = {f_p:.4f})"})
        for grp in ["district", "year"]:
            groups = [g.values for _, g in resid.groupby(p[grp].values)]
            st, pv = stats.levene(*groups, center="median")
            test_rows.append({"model": name, "test": f"Brown-Forsythe equal variance across {grp}s",
                              "stat": st, "p": pv, "note": f"{len(groups)} groups"})
        jb, jb_p, skew, kurt = jarque_bera(resid)
        test_rows.append({"model": name, "test": "Jarque-Bera normality", "stat": jb, "p": jb_p,
                          "note": f"skew = {skew:.3f}, kurtosis = {kurt:.3f}"})
        wd = wooldridge_ar1(p, rain)
        test_rows.append({"model": name, "test": "Wooldridge AR(1) serial correlation (H0: none)",
                          "stat": wd["F"], "p": wd["p"],
                          "note": f"F({wd['df1']},{wd['df2']}); coef on lagged FD resid = {wd['coef_u_lag']:.3f} "
                                  f"(-0.5 under H0), district-clustered SE {wd['se_cluster_district']:.3f}"})
        q = p.assign(e=resid.values).sort_values(["district", "year"])
        rho = q.e.corr(q.groupby("district").e.shift(1))
        test_rows.append({"model": name, "test": "AR(1) corr of within residuals (descriptive)", "stat": rho,
                          "p": np.nan, "note": "biased towards -1/(T-1) under no autocorrelation (small T), so a positive value understates it"})
        cd = pesaran_cd(p, resid)
        test_rows.append({"model": name, "test": "Pesaran CD cross-sectional dependence (H0: none)",
                          "stat": cd["CD"], "p": cd["p"],
                          "note": f"mean pairwise rho = {cd['mean_rho']:.3f}, mean |rho| = {cd['mean_abs_rho']:.3f}"})

        # Influence
        inf = OLSInfluence(res)
        dfb = pd.DataFrame(inf.dfbetas, columns=X.columns, index=p.index)
        idf = pd.DataFrame({"model": name, "district": p.district, "year": p.year, "ln_yield": p.ln_yield,
                            "fitted": fitted, "resid": resid, "leverage": inf.hat_matrix_diag,
                            "student_resid": inf.resid_studentized_external, "cooks_d": inf.cooks_distance[0]})
        for c in U.rain_terms(rain):
            idf[f"dfbetas_{c}"] = dfb[c]
        infl_rows.append(idf)

        # Leave-one-district-out
        rbar_all = p.groupby("district").R_season.mean().mean()
        tbar_all = p.groupby("district").T_season.mean().mean()
        cst = p.attrs["consts"]
        for d in [None] + list(dist_order):
            sub = p if d is None else p[p.district != d]
            r = U.fit_fe(sub, "ln_yield", rain)
            pct = np.exp(U.weather_lp(r.params, cst, R=rbar_all - C.RAIN_SHOCK_MM, T=tbar_all)
                         - U.weather_lp(r.params, cst, R=rbar_all, T=tbar_all)) - 1
            row = {"model": name, "dropped": d or "(none)", "n": int(r.nobs), "trend": r.params["trend"],
                   "pct_100mm_at_mean_R": float(pct), "Rbar_used_mm": rbar_all}
            for c in U.rain_terms(rain):
                row[c], row[f"se_{c}"] = r.params[c], r.std_errors[c]
            lodo_rows.append(row)

    tests = pd.DataFrame(test_rows)
    infl = pd.concat(infl_rows, ignore_index=True)
    lodo = pd.DataFrame(lodo_rows)

    out.log("DIAGNOSTIC TESTS")
    out.log(tests.to_string(index=False, float_format=lambda x: f"{x:.4f}", max_colwidth=90))
    n = len(p)
    out.log(f"\nINFLUENCE (rule of thumb: Cook's D > 4/n = {4 / n:.4f}; |student resid| > 3; "
            f"|DFBETAS| > 2/sqrt(n) = {2 / np.sqrt(n):.3f})")
    for name in MODELS:
        m = infl[infl.model == name]
        dcols = [c for c in m.columns if c.startswith("dfbetas_") and m[c].notna().any()]
        out.log(f"[{name}] Cook's D > 4/n: {(m.cooks_d > 4 / n).sum()} obs; |student resid| > 3: "
                f"{(m.student_resid.abs() > 3).sum()}; max leverage {m.leverage.max():.3f}")
        out.log(m.nlargest(8, "cooks_d")[["district", "year", "resid", "leverage", "student_resid", "cooks_d"] + dcols]
                .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    out.log("\nLEAVE-ONE-DISTRICT-OUT (100 mm effect at the mean of district mean R_season, T at its mean)")
    for name in MODELS:
        m = lodo[lodo.model == name]
        rcols = [c for c in m.columns if c.startswith(("Rc", "Tc")) and not c.startswith("se_") and m[c].notna().any()]
        out.log(f"[{name}]")
        out.log(m[["dropped", "n", "trend"] + rcols + ["pct_100mm_at_mean_R"]]
                .to_string(index=False, float_format=lambda x: f"{x:.6g}"))
        rest = m[m.dropped != "(none)"]
        out.log(f"  range of 100 mm effect across drops: {100 * rest.pct_100mm_at_mean_R.min():+.2f}% to "
                f"{100 * rest.pct_100mm_at_mean_R.max():+.2f}% (full sample "
                f"{100 * m[m.dropped == '(none)'].pct_100mm_at_mean_R.iat[0]:+.2f}%)")

    # Multicollinearity between R and T (A13 step 3)
    dm = p.copy()
    cols = ["Rc", "Rc_sq", "Tc", "Tc_sq", "trend"]
    for c in cols:
        dm[c + "_w"] = dm[c] - dm.groupby("district")[c].transform("mean")
    coll = []
    for name in MODELS:
        terms = ["trend"] + U.rain_terms(U.MODELS[name]["rain"])
        Xw = dm[[t + "_w" for t in terms]].to_numpy()
        for j, t in enumerate(terms):
            y_, X_ = Xw[:, j], np.delete(Xw, j, axis=1)
            b_ = np.linalg.lstsq(X_, y_, rcond=None)[0]
            r2 = 1 - ((y_ - X_ @ b_) ** 2).sum() / (y_ ** 2).sum()
            coll.append({"model": name, "term": t, "within_R2_on_others": r2, "VIF": 1 / (1 - r2)})
        Xs = Xw / Xw.std(axis=0)
        coll.append({"model": name, "term": "(condition number, standardised demeaned design)",
                     "within_R2_on_others": np.nan, "VIF": float(np.linalg.cond(Xs))})
    coll = pd.DataFrame(coll)
    r_rt = dm.Rc_w.corr(dm.Tc_w)
    out.log(f"\nMULTICOLLINEARITY R vs T: within-district corr(Rc, Tc) = {r_rt:.3f}; pooled corr = {p.Rc.corr(p.Tc):.3f}")
    out.log(coll.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    coll.loc[len(coll)] = {"model": "both", "term": "within corr(Rc, Tc)", "within_R2_on_others": np.nan, "VIF": r_rt}

    for df, nm in [(tests, "tests"), (infl, "influence"), (lodo, "leave_one_district_out"), (coll, "collinearity")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")

    # ---- Figures ----
    titles = {"M1": "M1 (linear in R and T)", "M2": "M2 (quadratic in R and T)"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, name in zip(axes, MODELS):
        m = infl[infl.model == name]
        for s in order:
            k = p.subdivision == s
            ax.scatter(m.fitted[k.values], m.resid[k.values], s=22, color=U.SUB_COLOR[s], marker=U.SUB_MARKER[s],
                       edgecolor="#fcfcfb", linewidth=0.8, label=U.SUB_LABEL[s])
        ax.axhline(0, color=U.INK2, lw=1)
        ax.set(title=titles[name], xlabel="Fitted ln(yield)")
    axes[0].set_ylabel("Residual (ln points)")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle("Residuals vs fitted", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'resid_vs_fitted'))}")

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, name in zip(axes, MODELS):
        z = infl[infl.model == name].student_resid.to_numpy()
        (osm, osr), (slope, icpt, _) = stats.probplot(z, dist="norm")
        ax.scatter(osm, osr, s=14, color="#2a78d6", edgecolor="#fcfcfb", linewidth=0.6)
        ax.plot(osm, slope * osm + icpt, color=U.INK2, lw=1)
        ax.set(title=titles[name], xlabel="Theoretical normal quantile")
    axes[0].set_ylabel("Studentized residual")
    fig.suptitle("Normal Q-Q plot of studentized residuals", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'qq'))}")

    for grp, label in [("year", "year"), ("district", "district")]:
        fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, sharey=True)
        cats = sorted(p.year.unique()) if grp == "year" else list(dist_order)
        for ax, name in zip(axes, MODELS):
            m = infl[infl.model == name]
            data = [m.resid[(m[grp] == c).values].to_numpy() for c in cats]
            ax.boxplot(data, widths=0.5, showfliers=False,
                       medianprops={"color": U.INK, "lw": 1.5}, boxprops={"color": U.MUTED},
                       whiskerprops={"color": U.MUTED}, capprops={"color": U.MUTED})
            for i, c in enumerate(cats, start=1):
                k = (m[grp] == c).values
                subs = p.subdivision[k].to_numpy()
                for s in order:
                    kk = subs == s
                    if kk.any():
                        ax.scatter(np.full(kk.sum(), i) + np.linspace(-0.15, 0.15, kk.sum()), m.resid[k][kk],
                                   s=14, color=U.SUB_COLOR[s], marker=U.SUB_MARKER[s], zorder=3,
                                   label=U.SUB_LABEL[s] if i == 1 or grp == "district" else None)
            ax.axhline(0, color=U.INK2, lw=1)
            ax.set(title=titles[name], ylabel="Residual (ln points)")
        axes[1].set_xticks(range(1, len(cats) + 1), [str(c) for c in cats], rotation=0 if grp == "year" else 45,
                           ha="center" if grp == "year" else "right")
        h, l = axes[0].get_legend_handles_labels()
        uniq = dict(zip(l, h))
        axes[0].legend(uniq.values(), uniq.keys(), frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
        fig.suptitle(f"Residuals by {label}", fontweight="bold", y=1.01)
        out.log(f"figure -> {U.rel(out.figure(fig, f'resid_by_{grp}'))}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, name in zip(axes, MODELS):
        m = lodo[(lodo.model == name) & (lodo.dropped != "(none)")]
        full = lodo[(lodo.model == name) & (lodo.dropped == "(none)")].pct_100mm_at_mean_R.iat[0]
        y = np.arange(len(m))
        ax.scatter(100 * m.pct_100mm_at_mean_R, y, s=30, color="#2a78d6", zorder=3)
        ax.axvline(100 * full, color=U.INK2, lw=1, ls="--")
        ax.set_ylim(-0.8, len(m) + 0.2)
        ax.text(100 * full, len(m) - 0.3, " full sample", color=U.INK2, fontsize=8, va="center")
        ax.set_yticks(y, m.dropped)
        ax.set(title=titles[name], xlabel="Yield change for -100 mm at mean R_season, T at mean (%)")
    axes[0].set_ylabel("District dropped")
    fig.suptitle("Leave-one-district-out stability of the 100 mm effect", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'leave_one_district_out'))}")
    out.close()


if __name__ == "__main__":
    main()
