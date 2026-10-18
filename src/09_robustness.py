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
