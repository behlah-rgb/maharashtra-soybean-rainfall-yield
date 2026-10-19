"""Step 9: robustness of the headline pair M1/M2 (SPEC A13.4d, A2, A5, A6, A10).

Usage: python src/09_robustness.py <panel.csv> <outdir> --wide-panel <panel_wide.csv>
  final: ... data/processed/panel_final.csv outputs/final --wide-panel data/processed/panel_final_wide.csv

Variants: base; drop_kolhapur_sangli; drop_2000_2003; drop_dq_flag; drop_boundary_sensitive (Akola, Parbhani,
Osmanabad, Chandrapur); year_fe (exploratory, rainfall is district-level); wider_districts (17); area_weighted;
drop_small_area (A2); trend_none, trend_district (A6); rainfall windows Jun-Jul, Jul-Sep, Jun-Sep (Rc built
from that window, centred at its own grand mean; T stays Jun-Sep); drop each drought year (DROUGHT_YEARS).
Summary per variant: 100 mm deficit in the model's rainfall window with T fixed (variant A), averaged over
districts of each district's effect at its own mean rainfall in the variant's sample (as in src/08). With T
fixed the temperature terms cancel. 95% interval: delta method on the year-clustered covariance (the
headline MBB intervals are in src/08). Centring constants: those of the main panel.
Area-weighting investigation (A9) for M1: weight concentration, between/within decomposition, district-
specific rainfall slopes, weighted leave-one-district-out.
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402

FORMS = ["M1", "M2"]


def effect_mean(res, df: pd.DataFrame, window: str, consts: dict) -> dict:
    """Mean over districts of exp(delta_d) - 1 for a 100 mm cut, with a delta-method CI."""
    rbar = df.groupby("district")[window].mean().to_numpy()
    r0 = (rbar - consts[window]) / C.RAIN_UNIT_MM
    r1 = r0 - C.RAIN_SHOCK_MM / C.RAIN_UNIT_MM
    terms = ["Rc"] + (["Rc_sq"] if "Rc_sq" in res.params.index else [])
    G = np.column_stack([r1 - r0] + ([r1 ** 2 - r0 ** 2] if len(terms) == 2 else []))   # districts x terms
    b = res.params[terms].to_numpy()
    e = np.exp(G @ b)
    pct = float(np.mean(e - 1))
    grad = (e[:, None] * G).mean(axis=0)
    V = res.cov.loc[terms, terms].to_numpy()
    se = float(np.sqrt(grad @ V @ grad))
    out = {"pct_100mm": pct, "pct_lo": pct - 1.96 * se, "pct_hi": pct + 1.96 * se, "se_pct": se,
           "b_Rc": res.params["Rc"], "se_Rc": res.std_errors["Rc"], "p_Rc": res.pvalues["Rc"],
           "b_Tc": res.params.get("Tc", np.nan), "p_Tc": res.pvalues.get("Tc", np.nan)}
    if "Rc_sq" in res.params.index:
        out.update({"b_Rc_sq": res.params["Rc_sq"], "p_Rc_sq": res.pvalues["Rc_sq"],
                    "b_Tc_sq": res.params["Tc_sq"], "p_Tc_sq": res.pvalues["Tc_sq"]})
    return out


def pct100(b: float) -> float:
    return float(np.exp(-b) - 1)            # b per 100 mm


def area_weighting_investigation(p: pd.DataFrame, out, plt) -> None:
    out.log("\n" + "=" * 92)
    out.log("AREA-WEIGHTING INVESTIGATION (A9), M1 (Rc, Tc), 100 mm effect with T fixed")
    out.log("=" * 92)
    q = p.copy()
    q["w_area"] = q.area_kha
    q["w_between"] = q.groupby("district").area_kha.transform("mean")
    q["w_within"] = q.area_kha / q.w_between
    dsh = q.groupby(["district", "subdivision"]).area_kha.sum().reset_index(name="weight")
    dsh["share"] = dsh.weight / dsh.weight.sum()
    dsh = dsh.sort_values("share", ascending=False)
    kish = 1.0 / np.sum(dsh.share ** 2)
    ysh = q.groupby("year").area_kha.sum() / q.area_kha.sum()
    half = int(np.median(q.year))
    out.log(f"Kish effective number of districts: {kish:.2f} of {len(dsh)}; subdivision shares: "
            + ", ".join(f"{U.SUB_LABEL.get(k, k)} {100 * v:.1f}%" for k, v in dsh.groupby('subdivision').share.sum().items())
            + f"; weight share of years > {half}: {100 * ysh[ysh.index > half].sum():.1f}% (unweighted "
            f"{100 * (q.year > half).mean():.1f}%)")
    dec = []
    for nm, w, desc in [("unweighted", None, "equal weights"), ("area", "w_area", "area_kha"),
                        ("between_only", "w_between", "district mean area, constant over time"),
                        ("within_only", "w_within", "area / district mean area")]:
        r = U.fit_fe(q, "ln_yield", U.MODELS["M1"]["rain"], weights=w)
        dec.append({"weights": nm, "definition": desc, "b_Rc_per_100mm": r.params["Rc"], "b_Tc": r.params["Tc"],
                    "pct_100mm": pct100(r.params["Rc"])})
    dec = pd.DataFrame(dec)
    out.log(dec.to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    ds = sorted(q.district.unique())
    for d in ds:
        q[f"Rx_{d}"] = q.Rc * (q.district == d)
    r = U.fit_fe(q, "ln_yield", {**{f"Rx_{d}": False for d in ds}, "Tc": False})
    sl = pd.DataFrame({"district": ds, "b_Rc_district": [r.params[f"Rx_{d}"] for d in ds],
                       "se_year_CR": [r.std_errors[f"Rx_{d}"] for d in ds]}).merge(dsh[["district", "subdivision", "share"]])
    sl["pct_100mm_district"] = [pct100(b) for b in sl.b_Rc_district]
    sl["pct_lo"] = [pct100(b + 1.96 * e) for b, e in zip(sl.b_Rc_district, sl.se_year_CR)]
    sl["pct_hi"] = [pct100(b - 1.96 * e) for b, e in zip(sl.b_Rc_district, sl.se_year_CR)]
    avg = {"unweighted mean of district slopes": sl.b_Rc_district.mean(),
           "area-share-weighted mean of district slopes": float(np.sum(sl.share * sl.b_Rc_district)),
           "pooled unweighted (base)": float(dec.b_Rc_per_100mm.iat[0]), "pooled area-weighted": float(dec.b_Rc_per_100mm.iat[1])}
    out.log(sl.sort_values("share", ascending=False).to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    for k, v in avg.items():
        out.log(f"  {k:45s} b = {v:.5g} -> 100 mm: {100 * pct100(v):+.2f}%")
    out.log(f"  correlation(area share, district slope) = {np.corrcoef(sl.share, sl.b_Rc_district)[0, 1]:.3f}")
    lodo = []
    for d in ds:
        rr = U.fit_fe(q[q.district != d], "ln_yield", U.MODELS["M1"]["rain"], weights="w_area")
        lodo.append({"dropped": d, "share_of_weight": float(dsh.set_index("district").share[d]),
                     "b_Rc": rr.params["Rc"], "pct_100mm": pct100(rr.params["Rc"])})
    lodo = pd.DataFrame(lodo).sort_values("share_of_weight", ascending=False)
    out.log(f"Weighted leave-one-district-out: 100 mm effect {100 * lodo.pct_100mm.min():+.2f}% to "
            f"{100 * lodo.pct_100mm.max():+.2f}%")
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
    ax.set(title="M1: district-specific 100 mm effects vs share of area weight",
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
    c = p.attrs["consts"]
    out.log(f"Panel: {U.describe_panel(p)}")
    out.log(f"Centring constants (main panel): {c}")

    V = [("base", "base", p, "R_season", "common", None, "M1/M2 as in src/06")]
    V.append(("drop_kolhapur_sangli", "A13 data quality", p[~p.district.isin(C.EXCLUDE_GHATS_DISTRICTS)], "R_season",
              "common", None, "drops " + ", ".join(C.EXCLUDE_GHATS_DISTRICTS)))
    V.append(("drop_2000_2003", "A13 data quality", p[~p.year.isin(C.EARLY_YEARS_DROP)], "R_season", "common", None,
              "drops " + ", ".join(map(str, C.EARLY_YEARS_DROP))))
    if "dq_flag" in p.columns:
        fl = p[p.dq_flag == 1]
        V.append(("drop_dq_flag", "A13 data quality", p[p.dq_flag == 0], "R_season", "common", None,
                  f"drops {len(fl)} rows: " + ", ".join(f"{r.district} {r.year}" for r in fl.itertuples())))
    V.append(("drop_boundary_sensitive", "A10 boundaries", p[~p.district.isin(C.BOUNDARY_SENSITIVE_DISTRICTS)], "R_season",
              "common", None, "drops " + ", ".join(C.BOUNDARY_SENSITIVE_DISTRICTS)))
    if U.rainfall_is_district_level(p):
        V.append(("year_fe", "A6 trend (exploratory)", p, "R_season", "year_fe", None, "year fixed effects, no trend"))
    else:
        out.log("year_fe SKIPPED: rainfall is subdivision-level in this panel.")
    if a.wide_panel is not None:
        w = U.load_panel(a.wide_panel, consts=c)
        extra = sorted(set(w.district) - set(p.district))
        assert extra == sorted(C.ROBUST_EXTRA_DISTRICTS)
        V.append(("wider_districts", "A5 districts", w, "R_season", "common", None, "adds " + ", ".join(extra)))
    else:
        out.log("wider_districts SKIPPED: no --wide-panel given.")
    V.append(("area_weighted", "A2 weights", p, "R_season", "common", "area_kha", "weights = area_kha"))
    small = p[p.area_kha < C.AREA_THRESHOLD]
    V.append(("drop_small_area", "A2 sample", p[p.area_kha >= C.AREA_THRESHOLD], "R_season", "common", None,
              f"drops {len(small)} rows with area < {C.AREA_THRESHOLD:g}k ha"))
    V.append(("trend_none", "A6 trend", p, "R_season", "none", None, "no trend"))
    V.append(("trend_district", "A6 trend", p, "R_season", "district", None, "district-specific linear trends"))
    for win, lab in [("R_early", "JunJul"), ("R_julsep", "JulSep"), ("R_season", "JunSep")]:
        V.append((f"window_{lab}", "rain window", p, win, "common", None, f"Rc from {win} (T stays Jun-Sep)"))
    for y in C.DROUGHT_YEARS:
        V.append((f"drop_{y}", "drop drought year", p[p.year != y], "R_season", "common", None, f"drops {y}"))

    rows = []
    for name, group, df, win, trend, wts, note in V:
        dfw = U.add_model_columns(df, c, rain_window=win)
        for form in FORMS:
            res = U.fit_fe(dfw, "ln_yield", U.MODELS[form]["rain"], trend=trend, weights=wts)
            r = {"variant": name, "group": group, "model": form, "rain_window": win, "trend": trend, "weights": wts or "",
                 "n": int(res.nobs), "districts": df.district.nunique(), "years": df.year.nunique(),
                 "within_r2": res.rsquared_within, "trend_coef": res.params.get("trend", np.nan), "note": note}
            r.update(effect_mean(res, dfw, win, c))
            rows.append(r)
    tab = pd.DataFrame(rows)
    base = tab[tab.variant == "base"].set_index("model")
    tab["pct_minus_base"] = tab.pct_100mm - tab.model.map(base.pct_100mm)

    out.log("\nROBUSTNESS: 100 mm deficit (T fixed), mean over districts at their own mean rainfall; 95% delta-method CI "
            "(year-clustered)")
    for form in FORMS:
        t = tab[tab.model == form].copy()
        t["effect"] = [f"{100 * r.pct_100mm:+6.2f}% [{100 * r.pct_lo:+.2f}, {100 * r.pct_hi:+.2f}]" for r in t.itertuples()]
        cols = ["variant", "n", "districts", "years", "b_Rc", "p_Rc", "b_Tc", "p_Tc"] + \
               (["b_Rc_sq", "p_Rc_sq", "b_Tc_sq", "p_Tc_sq"] if form == "M2" else []) + ["trend_coef", "within_r2", "effect"]
        out.log(f"\n[{form}]")
        out.log(t[cols].to_string(index=False, float_format=lambda x: f"{x:.4g}"))
        rr = t[t.variant != "base"]
        out.log(f"  range across variants: {100 * rr.pct_100mm.min():+.2f}% ({rr.loc[rr.pct_100mm.idxmin(), 'variant']}) to "
                f"{100 * rr.pct_100mm.max():+.2f}% ({rr.loc[rr.pct_100mm.idxmax(), 'variant']}); "
                f"base {100 * base.loc[form, 'pct_100mm']:+.2f}%")
    out.log("\nNotes per variant:")
    for r in tab[tab.model == "M1"].itertuples():
        out.log(f"  {r.variant}: {r.note}")
    out.log("Window variants: 100 mm is a larger share of a shorter window, so they are not directly comparable.")
    out.log(f"table -> {U.rel(out.table(tab, 'results'))}")

    area_weighting_investigation(p, out, plt)

    names = list(dict.fromkeys(tab.variant))
    fig, axes = plt.subplots(1, 2, figsize=(11, 0.4 * len(names) + 1.5), sharey=True)
    for ax, form in zip(axes, FORMS):
        t = tab[tab.model == form].set_index("variant").loc[names]
        y = np.arange(len(names))[::-1]
        ax.errorbar(100 * t.pct_100mm, y, xerr=[100 * (t.pct_100mm - t.pct_lo), 100 * (t.pct_hi - t.pct_100mm)],
                    fmt="o", color="#2a78d6", ms=5, lw=1.2, capsize=0)
        ax.axvline(100 * base.loc[form, "pct_100mm"], color=U.INK2, lw=1, ls="--")
        ax.axvline(0, color=U.INK, lw=1)
        ax.set_yticks(y, names)
        ax.set(title=form, xlabel="Yield change for a 100 mm deficit, T fixed (%)")
    fig.suptitle("Robustness of the 100 mm effect (dashed = base; 95% delta-method CI, year-clustered)",
                 fontweight="bold", y=1.0)
    out.log(f"figure -> {U.rel(out.figure(fig, 'forest'))}")
    out.log("Results are associations under the model's assumptions, not causal effects.")
    out.close()


if __name__ == "__main__":
    main()
