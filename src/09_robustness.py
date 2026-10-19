"""Step 9: robustness of the headline models (linear and quadratic in rainfall, ln yield).

Usage: python src/09_robustness.py <panel.csv> <outdir> [--wide-panel <panel_wide.csv>]
  prototype: ... data/processed/panel_v1.csv outputs/prototype --wide-panel data/processed/panel_v1_wide.csv
  final    : ... data/processed/panel_final.csv outputs/final --wide-panel data/processed/panel_final_wide.csv

Variants (SPEC Amendments 2026-10-18):
  base                         common trend, all rows, R_season (Jun-Sep)
  A2a drop_small_area          drop district-years with area < AREA_THRESHOLD thousand ha
  A2b area_weighted            PanelOLS weights = area_kha
  A5  wider_districts          13 + ROBUST_EXTRA_DISTRICTS (needs --wide-panel)
  A6  trend_none / trend_district / year_fe   (year_fe only if rainfall is district-level)
  windows                      R = Jun-Jul (R_early), Jul-Sep (R_julsep), Jun-Sep (R_season = base)
  drop_<year>                  drop each DROUGHT_YEARS year in turn
  A10 drop_boundary_sensitive  drop BOUNDARY_SENSITIVE_DISTRICTS (Akola, Parbhani, Osmanabad, Chandrapur)

Area-weighting investigation (SPEC A9), linear model: weight concentration (district and year shares of
total area weight, Kish effective number of districts), decomposition into cross-district weights
(district mean area, constant over time) and within-district weights (area / district mean area),
district-specific rainfall slopes and their unweighted vs area-weighted averages, and
leave-one-district-out under area weights.

Summary effect per variant: 100 mm deficit in the model's rainfall window, evaluated at Rbar = mean over
districts of each district's mean rainfall in that variant's sample. pct = exp(delta) - 1, with a 95%
delta-method interval from the year-clustered covariance (exp(delta +/- 1.96 se) - 1). No bootstrap here.
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402

FORMS = {"linear": False, "quadratic": True}


def summarise(res, df: pd.DataFrame, var: str, sq: bool) -> dict:
    rbar = df.groupby("district")[var].mean().mean()
    old, new = rbar, rbar - C.RAIN_SHOCK_MM
    terms = [var] + ([f"{var}_sq"] if sq else [])
    g = np.array([new - old] + ([new ** 2 - old ** 2] if sq else []))
    b = res.params[terms].to_numpy()
    V = res.cov.loc[terms, terms].to_numpy()
    delta, se = float(g @ b), float(np.sqrt(g @ V @ g))
    out = {"Rbar_mm": rbar, "delta_ln": delta, "se_delta": se, "pct_100mm": np.exp(delta) - 1,
           "pct_lo": np.exp(delta - 1.96 * se) - 1, "pct_hi": np.exp(delta + 1.96 * se) - 1,
           "b_R": res.params[var], "se_R": res.std_errors[var], "p_R": res.pvalues[var]}
    if sq:
        out.update({"b_R_sq": res.params[f"{var}_sq"], "se_R_sq": res.std_errors[f"{var}_sq"],
                    "p_R_sq": res.pvalues[f"{var}_sq"]})
    return out


def pct100(b: float) -> float:
    return float(np.exp(-C.RAIN_SHOCK_MM * b) - 1)


def area_weighting_investigation(p: pd.DataFrame, out, plt) -> None:
    """Why does area weighting move the 100 mm effect (SPEC A9)? Linear model in R_season."""
    out.log("\n" + "=" * 92)
    out.log("AREA-WEIGHTING INVESTIGATION (SPEC A9), linear model in R_season")
    out.log("=" * 92)
    q = p.copy()
    q["w_area"] = q.area_kha
    q["w_between"] = q.groupby("district").area_kha.transform("mean")      # cross-district only
    q["w_within"] = q.area_kha / q.w_between                               # over time only
    # 1. Weight concentration
    dsh = q.groupby(["district", "subdivision"]).area_kha.sum().reset_index(name="weight")
    dsh["share"] = dsh.weight / dsh.weight.sum()
    dsh = dsh.sort_values("share", ascending=False)
    kish = 1.0 / np.sum(dsh.share ** 2)
    sub = dsh.groupby("subdivision").share.sum()
    ysh = q.groupby("year").area_kha.sum()
    ysh = ysh / ysh.sum()
    half = int(np.median(q.year))
    out.log(f"Kish effective number of districts under area weights: {kish:.2f} of {len(dsh)}")
    out.log("Weight share by subdivision: " + ", ".join(f"{U.SUB_LABEL.get(k, k)} {100 * v:.1f}%" for k, v in sub.items()))
    out.log(f"Weight share of years > {half}: {100 * ysh[ysh.index > half].sum():.1f}% "
            f"(unweighted: {100 * (q.year > half).mean():.1f}%)")
    out.log("District shares of total area weight:")
    out.log(dsh.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # 2. Decomposition
    dec = []
    for nm, w, desc in [("unweighted", None, "equal weights"), ("area", "w_area", "area_kha (as in area_weighted)"),
                        ("between_only", "w_between", "district mean area, constant over time"),
                        ("within_only", "w_within", "area / district mean area (time profile only)")]:
        r = U.fit_fe(q, "ln_yield", {"R_season": False}, weights=w)
        dec.append({"weights": nm, "definition": desc, "b_R": r.params["R_season"], "se_year_CR": r.std_errors["R_season"],
                    "trend": r.params["trend"], "pct_100mm": pct100(r.params["R_season"])})
    dec = pd.DataFrame(dec)
    out.log("\nDecomposition of the weighting effect:")
    out.log(dec.to_string(index=False, float_format=lambda x: f"{x:.5g}"))

    # 3. District-specific slopes (entity effects + common trend + R x district)
    ds = sorted(q.district.unique())
    for d in ds:
        q[f"Rx_{d}"] = q.R_season * (q.district == d)
    r = U.fit_fe(q, "ln_yield", {f"Rx_{d}": False for d in ds})
    sl = pd.DataFrame({"district": ds, "b_R_district": [r.params[f"Rx_{d}"] for d in ds],
                       "se_year_CR": [r.std_errors[f"Rx_{d}"] for d in ds]})
    sl = sl.merge(dsh[["district", "subdivision", "share"]], on="district")
    sl["pct_100mm_district"] = [pct100(b) for b in sl.b_R_district]
    vR = q.groupby("district").R_season.var()
    sl["var_R_within"] = sl.district.map(vR)
    avg = {"unweighted mean of district slopes": sl.b_R_district.mean(),
           "area-share-weighted mean of district slopes": float(np.sum(sl.share * sl.b_R_district)),
           "pooled unweighted (base)": float(dec.b_R[dec.weights == "unweighted"].iat[0]),
           "pooled area-weighted": float(dec.b_R[dec.weights == "area"].iat[0])}
    corr = float(np.corrcoef(sl.share, sl.b_R_district)[0, 1])
    out.log(f"\nDistrict-specific rainfall slopes (common trend; within R2 = {r.rsquared_within:.4f}):")
    out.log(sl.sort_values("share", ascending=False).to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    for k, v in avg.items():
        out.log(f"  {k:45s} b = {v:.6g}  -> 100 mm: {100 * pct100(v):+.2f}%")
    out.log(f"  correlation(area share, district slope) = {corr:.3f}")

    # 4. Leave-one-district-out under area weights
    lodo = []
    for d in ds:
        rr = U.fit_fe(q[q.district != d], "ln_yield", {"R_season": False}, weights="w_area")
        lodo.append({"dropped": d, "share_of_weight": float(dsh.set_index("district").share[d]),
                     "b_R": rr.params["R_season"], "pct_100mm": pct100(rr.params["R_season"])})
    lodo = pd.DataFrame(lodo).sort_values("share_of_weight", ascending=False)
    out.log("\nLeave-one-district-out under area weights:")
    out.log(lodo.to_string(index=False, float_format=lambda x: f"{x:.5g}"))

    # pct100 is decreasing in b: the lower percent bound comes from b + 1.96 se.
    sl["pct_lo"] = [pct100(b + 1.96 * e) for b, e in zip(sl.b_R_district, sl.se_year_CR)]
    sl["pct_hi"] = [pct100(b - 1.96 * e) for b, e in zip(sl.b_R_district, sl.se_year_CR)]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for s_ in [x for x in U.SUB_ORDER if x in set(sl.subdivision)]:
        k = sl.subdivision == s_
        ax.errorbar(100 * sl.share[k], 100 * sl.pct_100mm_district[k],
                    yerr=[100 * (sl.pct_100mm_district[k] - sl.pct_lo[k]), 100 * (sl.pct_hi[k] - sl.pct_100mm_district[k])],
                    fmt=U.SUB_MARKER[s_], color=U.SUB_COLOR[s_], ms=6, lw=1, capsize=0, label=U.SUB_LABEL[s_])
    for r_ in sl.itertuples():
        ax.annotate(r_.district, (100 * r_.share, 100 * r_.pct_100mm_district), fontsize=7, color=U.INK2,
                    xytext=(4, 2), textcoords="offset points")
    for k, ls in [("pooled unweighted (base)", "--"), ("pooled area-weighted", ":")]:
        ax.axhline(100 * pct100(avg[k]), color=U.INK2, lw=1, ls=ls)
        ax.text(ax.get_xlim()[1], 100 * pct100(avg[k]), f" {k}", fontsize=7, color=U.INK2, va="center")
    ax.axhline(0, color=U.INK, lw=1)
    ax.set(title="District-specific 100 mm effects vs share of area weight",
           xlabel="Share of total area weight (%)", ylabel="Yield change for a 100 mm deficit (%)")
    ax.legend(frameon=False, loc="upper center")
    out.log(f"figure -> {U.rel(out.figure(fig, 'area_weighting'))}")
    for df, nm in [(dsh, "weight_shares"), (dec, "weighting_decomposition"), (sl, "district_slopes"),
                   (lodo, "weighted_leave_one_district_out")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0], wide=True)
    out = U.Outputs(a.outdir, "09_robust", a.panel)
    plt = U.setup_matplotlib()
    p = U.load_panel(a.panel)
    out.log(f"Panel: {U.describe_panel(p)}")
    district_level = U.rainfall_is_district_level(p)

    variants = [  # (name, group, data, rain var, trend, weights, note)
        ("base", "base", p, "R_season", "common", None, "common trend, all rows, Jun-Sep"),
    ]
    small = p[p.area_kha < C.AREA_THRESHOLD]
    variants.append(("drop_small_area", "A2 sample/weights", p[p.area_kha >= C.AREA_THRESHOLD], "R_season", "common",
                     None, f"drops {len(small)} rows: " + ", ".join(f"{r.district} {r.year}" for r in small.itertuples())))
    variants.append(("area_weighted", "A2 sample/weights", p, "R_season", "common", "area_kha", "weights = area_kha"))
    if a.wide_panel is not None:
        w = U.load_panel(a.wide_panel)
        extra = sorted(set(w.district) - set(p.district))
        assert sorted(extra) == sorted(C.ROBUST_EXTRA_DISTRICTS), f"wide panel extras {extra} != config"
        assert set(p.district) <= set(w.district)
        out.log(f"Wider panel {U.rel(a.wide_panel)}: {U.describe_panel(w)}")
        variants.append(("wider_districts", "A5 districts", w, "R_season", "common", None, f"adds {', '.join(extra)}"))
    else:
        out.log("SKIPPED wider_districts: no --wide-panel given.")
    variants.append(("trend_none", "A6 trend", p, "R_season", "none", None, "no trend"))
    variants.append(("trend_district", "A6 trend", p, "R_season", "district", None, "district-specific linear trends"))
    skipped = []
    if district_level:
        variants.append(("year_fe", "A6 trend", p, "R_season", "year_fe", None, "year fixed effects, no trend"))
    else:
        skipped.append({"variant": "year_fe", "group": "A6 trend",
                        "note": "SKIPPED: rainfall is subdivision-level in this panel (SPEC A6 allows year FE only "
                                "with district-level rainfall)."})
        out.log("year_fe " + skipped[-1]["note"])
    variants.append(("window_JunJul", "rain window", p, "R_early", "common", None, "R = Jun-Jul"))
    variants.append(("window_JulSep", "rain window", p, "R_julsep", "common", None, "R = Jul-Sep"))
    variants.append(("window_JunSep", "rain window", p, "R_season", "common", None, "R = Jun-Sep (same as base)"))
    for y in C.DROUGHT_YEARS:
        if y in set(p.year):
            variants.append((f"drop_{y}", "drop drought year", p[p.year != y], "R_season", "common", None, f"drops {y}"))
        else:
            skipped.append({"variant": f"drop_{y}", "group": "drop drought year", "note": f"SKIPPED: {y} not in panel"})

    keep = p[~p.district.isin(C.BOUNDARY_SENSITIVE_DISTRICTS)]
    assert set(C.BOUNDARY_SENSITIVE_DISTRICTS) <= set(p.district)
    variants.append(("drop_boundary_sensitive", "A10 boundaries", keep, "R_season", "common", None,
                     "drops " + ", ".join(C.BOUNDARY_SENSITIVE_DISTRICTS)))

    rows = []
    for name, group, df, var, trend, wts, note in variants:
        for form, sq in FORMS.items():
            res = U.fit_fe(df, "ln_yield", {var: sq}, trend=trend, weights=wts)
            r = {"variant": name, "group": group, "model": form, "rain_var": var, "trend": trend,
                 "weights": wts or "", "n": int(res.nobs), "districts": df.district.nunique(),
                 "years": df.year.nunique(), "within_r2": res.rsquared_within,
                 "trend_coef": res.params.get("trend", np.nan), "note": note}
            r.update(summarise(res, df, var, sq))
            rows.append(r)
    tab = pd.DataFrame(rows)
    base = tab[tab.variant == "base"].set_index("model")
    tab["pct_minus_base"] = tab.pct_100mm - tab.model.map(base.pct_100mm)

    out.log("\nROBUSTNESS: 100 mm deficit at mean rainfall of the variant's window (95% delta-method CI, "
            "year-clustered)")
    for form in FORMS:
        t = tab[tab.model == form].copy()
        t["effect"] = [f"{100 * r.pct_100mm:+6.2f}% [{100 * r.pct_lo:+.2f}, {100 * r.pct_hi:+.2f}]" for r in t.itertuples()]
        cols = ["variant", "group", "n", "districts", "years", "rain_var", "Rbar_mm", "b_R", "se_R"] + \
               (["b_R_sq", "se_R_sq", "p_R_sq"] if FORMS[form] else ["p_R"]) + ["trend_coef", "within_r2", "effect"]
        out.log(f"\n[{form}]")
        out.log(t[cols].to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    out.log("\nNotes per variant:")
    for r in tab[tab.model == "linear"].itertuples():
        out.log(f"  {r.variant}: {r.note}")
    for s in skipped:
        out.log(f"  {s['variant']}: {s['note']}")
    out.log("Window variants change what '100 mm' means: 100 mm is a larger share of a shorter window.")

    out.log(f"table -> {U.rel(out.table(tab, 'results'))}")
    if skipped:
        out.log(f"table -> {U.rel(out.table(pd.DataFrame(skipped), 'skipped'))}")

    area_weighting_investigation(p, out, plt)

    fig, axes = plt.subplots(1, 2, figsize=(11, 0.42 * tab.variant.nunique() + 1.5), sharey=True)
    names = list(dict.fromkeys(tab.variant))
    for ax, form in zip(axes, FORMS):
        t = tab[tab.model == form].set_index("variant").loc[names]
        y = np.arange(len(names))[::-1]
        ax.errorbar(100 * t.pct_100mm, y, xerr=[100 * (t.pct_100mm - t.pct_lo), 100 * (t.pct_hi - t.pct_100mm)],
                    fmt="o", color="#2a78d6", ms=5, lw=1.2, capsize=0)
        ax.axvline(100 * base.loc[form, "pct_100mm"], color=U.INK2, lw=1, ls="--")
        ax.axvline(0, color=U.INK, lw=1)
        ax.set_yticks(y, names)
        ax.set(title=f"{form.capitalize()} in rainfall", xlabel="Yield change for a 100 mm deficit (%)")
    fig.suptitle("Robustness of the 100 mm deficit effect (dashed = base; 95% delta-method CI)",
                 fontweight="bold", y=1.0)
    out.log(f"figure -> {U.rel(out.figure(fig, 'forest'))}")
    out.log("Results are associations under the model's assumptions, not causal effects.")
    out.close()


if __name__ == "__main__":
    main()
