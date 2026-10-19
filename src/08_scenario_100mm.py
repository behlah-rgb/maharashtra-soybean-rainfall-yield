"""Step 8: 100 mm deficit and weak-monsoon scenarios (SPEC A13.3).

Usage: python src/08_scenario_100mm.py <panel.csv> <outdir>   (run src/06 first: the headline model is read
from <outdir>/tables/06_models_linear_vs_quadratic.csv, rule A11.1)

Per district d: Rbar_d, Tbar_d = district means over the panel years; Ybar_d = district mean observed yield
(kg/ha baseline, A9); s_d = within-district OLS slope of T_season on R_season.
Change in ln yield = lp(R_new, T_new) - lp(Rbar_d, Tbar_d), lp = fitted weather part of the model
(pipeline_utils.weather_lp). pct = exp(change) - 1 (headline unit); kg/ha = pct x Ybar_d.
  Variant A (headline): T_new = Tbar_d (temperature held fixed, ceteris paribus).
  Variant B (exploratory): T_new = Tbar_d + s_d (R_new - Rbar_d).
Scenarios: deficit_100mm (R_new = Rbar_d - 100); surplus_100mm (R_new = Rbar_d + 100; symmetry check, A14.5d); weak_monsoon_90pct / 80pct (R_new = 0.9 / 0.8 Rbar_d),
both variants. Models: M1 and M2 (the headline pair); exploratory: M2_rain_only (variants A and B) and
the timing model (100 mm split across Jun-Jul and Aug-Sep in proportion to each window's share of
Rbar_d (A3); T and dry_spell_max fixed).
Range curve: deficit from R to R - 100 for R in [min + 100, max] of R_season, T at the panel mean.
Intervals: 95% percentile, moving-block bootstrap over years L = BLOCK_LENGTH (headline), L in
BLOCK_LENGTH_SENSITIVITY, and the district bootstrap (check); N_BOOT_BLOCK reps; seeds config.BOOT_SEEDS.
Every replication refits the model AND re-estimates s_d from the replication's years. Rbar, Tbar, Ybar are
held at sample values. Subdivision and state rows = unweighted means of district rows.
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402

PAIR = ["M1", "M2"]
EXPLORATORY = ["M2_rain_only", "timing"]
HEAD = f"L{C.BLOCK_LENGTH}"
BASELINE_NOTE = "kg/ha baseline = district mean observed yield over the panel years"
SHORT = {"MADHYA MAHARASHTRA": "Madhya M."}


def slopes(p: pd.DataFrame, rows: np.ndarray, codes: np.ndarray, n_d: int) -> np.ndarray:
    """Within-district OLS slope of T_season on R_season for each district (on the given rows)."""
    R, T = p.R_season.to_numpy()[rows], p.T_season.to_numpy()[rows]
    cnt = np.bincount(codes, minlength=n_d)
    Rm = np.bincount(codes, R, minlength=n_d) / cnt
    Tm = np.bincount(codes, T, minlength=n_d) / cnt
    sxy = np.bincount(codes, (R - Rm[codes]) * (T - Tm[codes]), minlength=n_d)
    sxx = np.bincount(codes, (R - Rm[codes]) ** 2, minlength=n_d)
    with np.errstate(invalid="ignore", divide="ignore"):
        return sxy / sxx


def scenario_effects(params: dict, c: dict, dm: pd.DataFrame, s_d: np.ndarray) -> dict:
    """{(model, scenario, variant): pct array over districts}."""
    Rb, Tb = dm.R_season.to_numpy(), dm.T_season.to_numpy()
    Reb, Rlb = dm.R_early.to_numpy(), dm.R_late.to_numpy()
    out = {}
    news = {"deficit_100mm": Rb - C.RAIN_SHOCK_MM, "surplus_100mm": Rb + C.RAIN_SHOCK_MM}   # surplus: A14.5d symmetry
    for fr in C.WEAK_MONSOON_FRACTIONS:
        news[f"weak_monsoon_{round(100 * fr)}pct"] = fr * Rb
    for m in PAIR + ["M2_rain_only"]:
        b = params[m]
        base = U.weather_lp(b, c, R=Rb, T=Tb)
        for sc, Rn in news.items():
            for var, Tn in [("A", Tb), ("B", Tb + s_d * (Rn - Rb))]:
                out[(m, sc, var)] = np.exp(U.weather_lp(b, c, R=Rn, T=Tn) - base) - 1
    de = C.RAIN_SHOCK_MM * Reb / Rb
    b = params["timing"]
    out[("timing", "deficit_100mm_split", "A")] = np.exp(U.weather_lp(b, c, Re=Reb - de, Rl=Rlb - (C.RAIN_SHOCK_MM - de))
                                                         - U.weather_lp(b, c, Re=Reb, Rl=Rlb)) - 1
    return out


def range_curve(params: dict, c: dict, grid: np.ndarray) -> dict:
    T0 = c["T_season"]
    return {m: np.exp(U.weather_lp(params[m], c, R=grid - C.RAIN_SHOCK_MM, T=T0) - U.weather_lp(params[m], c, R=grid, T=T0)) - 1
            for m in PAIR}


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "08_scenario", a.panel)
    plt = U.setup_matplotlib()
    p = U.load_panel(a.panel)
    c = p.attrs["consts"]
    out.log(f"Panel: {U.describe_panel(p)}")
    vfile = a.outdir / "tables" / "06_models_linear_vs_quadratic.csv"
    assert vfile.exists(), f"run src/06 first ({U.rel(vfile)} missing)"
    vd = pd.read_csv(vfile, comment="#").set_index("linear_model")
    headline, sens, verdict = vd.loc["M1", "headline_model"], vd.loc["M1", "sensitivity_model"], vd.loc["M1", "verdict"]
    out.log(f"Verdict (06): {verdict} -> HEADLINE {headline}, sensitivity {sens} (rule A11.1). Headline variant: A "
            f"(T fixed). Percent is the headline unit; {BASELINE_NOTE}.")

    dm = p.groupby("district").agg(subdivision=("subdivision", "first"), R_season=("R_season", "mean"),
                                   T_season=("T_season", "mean"), R_early=("R_early", "mean"), R_late=("R_late", "mean"),
                                   Ybar_kgha=("yield_kgha", "mean")).reset_index()
    assert list(dm.district) == list(pd.unique(p.district))
    codes0 = pd.factorize(p.district)[0]
    n_d = len(dm)
    dm["s_T_on_R_per_100mm"] = 100 * slopes(p, np.arange(len(p)), codes0, n_d)
    out.log("District means (Rbar mm, Tbar deg C, Ybar kg/ha) and within-district slope of T on R (deg C per 100 mm):")
    out.log(dm.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    ybar = dm.Ybar_kgha.to_numpy()

    models = PAIR + EXPLORATORY
    fes, point = {}, {}
    for m in models:
        s = U.MODELS[m]
        res = U.fit_fe(p, s["outcome"], s["rain"])
        fes[m] = U.FastFE(p, s["outcome"], s["rain"])
        assert np.allclose(res.params[fes[m].cols].to_numpy(), fes[m].fit(np.arange(len(p))), rtol=1e-7, atol=1e-12)
        point[m] = res.params
    s0 = slopes(p, np.arange(len(p)), codes0, n_d)
    pe = scenario_effects(point, c, dm, s0)
    grid = np.linspace(p.R_season.min() + C.RAIN_SHOCK_MM, p.R_season.max(), C.RANGE_GRID_POINTS)
    pc = range_curve(point, c, grid)

    years, yrows = U.year_rows(p)
    schemes = {f"L{L}": [(U.rows_from_year_draw(yrows, d), None)
                         for d in U.block_draws(len(years), L, C.N_BOOT_BLOCK, C.BOOT_SEEDS[f"block_L{L}"])]
               for L in [C.BLOCK_LENGTH] + list(C.BLOCK_LENGTH_SENSITIVITY)}
    schemes["districts"] = [U.rows_from_district_draw(p, d)
                            for d in U.district_draws(n_d, C.N_BOOT_BLOCK, C.BOOT_SEEDS["districts"])]
    boot = {}
    for kind, draws in schemes.items():
        eff = {k: [] for k in pe}
        curve = {m: [] for m in PAIR}
        for rows, codes in draws:
            prm = {m: pd.Series(fes[m].fit(rows, codes), index=fes[m].cols) for m in models}
            if codes is None:                       # year draws: districts keep their codes
                sd = slopes(p, rows, codes0[rows], n_d)
            else:                                   # district draws: a district's own rows are unchanged
                sd = s0
            for k, v in scenario_effects(prm, c, dm, sd).items():
                eff[k].append(v)
            for m, v in range_curve(prm, c, grid).items():
                curve[m].append(v)
        boot[kind] = ({k: np.array(v) for k, v in eff.items()}, {m: np.array(v) for m, v in curve.items()})
        seed = C.BOOT_SEEDS["districts" if kind == "districts" else f"block_{kind}"]
        out.log(f"Bootstrap {kind}: {len(draws)} reps, seed {seed}")

    def ci(arr):
        return np.nanpercentile(arr, 2.5, axis=0), np.nanpercentile(arr, 97.5, axis=0)

    kinds = list(schemes)
    groups = [(g, (dm.subdivision == g).to_numpy()) for g in sorted(dm.subdivision.unique())]
    groups.append(("ALL DISTRICTS", np.ones(n_d, bool)))
    rows = []
    for (m, sc, var), pct in pe.items():
        role = ("HEADLINE" if (m == headline and var == "A" and sc == "deficit_100mm") else
                "headline model" if (m == headline and var == "A") else "sensitivity" if m in PAIR else "exploratory")
        lab = "ILLUSTRATIVE" if sc.startswith("weak") else "symmetry check" if sc.startswith("surplus") else "main"
        units = [("district", d.district, d.subdivision, np.arange(n_d) == i) for i, d in dm.iterrows()]
        units += [("subdivision" if g != "ALL DISTRICTS" else "state", g, g, k) for g, k in groups]
        for level, unit, sub, k in units:
            r = {"model": m, "scenario": sc, "variant": var, "role": role, "label": lab, "kgha_baseline": BASELINE_NOTE,
                 "level": level, "unit": unit, "subdivision": sub, "Rbar_mm": dm.R_season[k].mean(),
                 "Tbar_C": dm.T_season[k].mean(), "Ybar_kgha": dm.Ybar_kgha[k].mean(),
                 "pct": pct[k].mean(), "kgha": (pct * ybar)[k].mean()}
            for kind in kinds:
                bd = boot[kind][0][(m, sc, var)]
                lo, hi = ci(bd[:, k].mean(axis=1))
                klo, khi = ci((bd * ybar)[:, k].mean(axis=1))
                r.update({f"pct_lo_{kind}": lo, f"pct_hi_{kind}": hi, f"kgha_lo_{kind}": klo, f"kgha_hi_{kind}": khi})
            rows.append(r)
    tab = pd.DataFrame(rows)

    def fmt(df):
        d = df.copy()
        d["pct [MBB L3] {districts}"] = [
            f"{100 * r['pct']:+6.1f}% [{100 * r[f'pct_lo_{HEAD}']:+.1f}, {100 * r[f'pct_hi_{HEAD}']:+.1f}] "
            f"{{{100 * r['pct_lo_districts']:+.1f}, {100 * r['pct_hi_districts']:+.1f}}}" for _, r in d.iterrows()]
        for L in C.BLOCK_LENGTH_SENSITIVITY:
            d[f"MBB L{L}"] = [f"[{100 * r[f'pct_lo_L{L}']:+.1f}, {100 * r[f'pct_hi_L{L}']:+.1f}]" for _, r in d.iterrows()]
        d["kg/ha [MBB L3]"] = [f"{r['kgha']:+7.1f} [{r[f'kgha_lo_{HEAD}']:+.1f}, {r[f'kgha_hi_{HEAD}']:+.1f}]"
                               for _, r in d.iterrows()]
        return d[["model", "scenario", "variant", "role", "unit", "pct [MBB L3] {districts}"]
                 + [f"MBB L{L}" for L in C.BLOCK_LENGTH_SENSITIVITY] + ["kg/ha [MBB L3]"]]

    st = tab[tab.level == "state"]
    hl = st[(st.model == headline) & (st.scenario == "deficit_100mm") & (st.variant == "A")].iloc[0]
    out.log("\n" + "=" * 100)
    out.log(f"HEADLINE: 100 mm deficit, {headline}, variant A (T fixed), mean of the 13 districts: "
            f"{100 * hl.pct:+.2f}% [MBB L{C.BLOCK_LENGTH} 95%: {100 * hl[f'pct_lo_{HEAD}']:+.2f}, {100 * hl[f'pct_hi_{HEAD}']:+.2f}]; "
            f"{hl.kgha:+.1f} kg/ha [{hl[f'kgha_lo_{HEAD}']:+.1f}, {hl[f'kgha_hi_{HEAD}']:+.1f}]")
    if bool(vd.loc["M1", "report_range_across_both"]):
        o = st[(st.model == sens) & (st.scenario == "deficit_100mm") & (st.variant == "A")].iloc[0]
        out.log(f"Range across {headline} and {sens} (A11.1): {100 * min(hl.pct, o.pct):+.2f}% to {100 * max(hl.pct, o.pct):+.2f}%")
    out.log("=" * 100)
    out.log(f"\nSTATE and SUBDIVISION rows (unweighted means of districts); {BASELINE_NOTE}. [..] MBB L3 (headline "
            "intervals); {..} district bootstrap (check); L2/L4 sensitivity.")
    out.log(fmt(tab[tab.level != "district"].sort_values(["model", "scenario", "variant", "level"]))
            .to_string(index=False))
    out.log(f"\nDISTRICT rows, {headline} and {sens}, 100 mm deficit:")
    out.log(fmt(tab[(tab.level == "district") & tab.model.isin(PAIR) & (tab.scenario == "deficit_100mm")])
            .to_string(index=False))
    out.log("\nWeak-monsoon rows are ILLUSTRATIVE. Variant B and the M2_rain_only / timing rows are exploratory.")

    crow = []
    for m in PAIR:
        for j, R in enumerate(grid):
            r = {"model": m, "R_from_mm": R, "R_to_mm": R - C.RAIN_SHOCK_MM, "T_C": c["T_season"], "pct": pc[m][j]}
            for kind in kinds:
                lo, hi = ci(boot[kind][1][m][:, j])
                r.update({f"pct_lo_{kind}": lo, f"pct_hi_{kind}": hi})
            crow.append(r)
    curve = pd.DataFrame(crow)
    sel = curve[curve.R_from_mm.isin(grid[[0, len(grid) // 4, len(grid) // 2, 3 * len(grid) // 4, -1]])]
    out.log(f"\nRange curve (T at panel mean {c['T_season']:.2f} deg C):")
    out.log(sel[["model", "R_from_mm", "pct", f"pct_lo_{HEAD}", f"pct_hi_{HEAD}"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    for df, nm in [(tab, "results"), (curve, "range_curve"), (dm, "district_means")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")

    # Figures
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, m in zip(axes, PAIR):
        q = curve[curve.model == m]
        ax.fill_between(q.R_from_mm, 100 * q[f"pct_lo_{HEAD}"], 100 * q[f"pct_hi_{HEAD}"], color="#86b6ef", alpha=0.45, lw=0,
                        label=f"95% moving-block bootstrap (L={C.BLOCK_LENGTH})")
        ax.plot(q.R_from_mm, 100 * q.pct_lo_districts, color=U.MUTED, lw=1, ls=":", label="95% district bootstrap")
        ax.plot(q.R_from_mm, 100 * q.pct_hi_districts, color=U.MUTED, lw=1, ls=":")
        ax.plot(q.R_from_mm, 100 * q.pct, color="#1c5cab", lw=2, label="Point estimate")
        ax.axhline(0, color=U.INK2, lw=1)
        for g in sorted(dm.subdivision.unique()):
            r_ = dm.R_season[dm.subdivision == g].mean()
            ax.axvline(r_, color=U.SUB_COLOR.get(g, U.MUTED), lw=1, ls="--")
            ax.text(r_, 0.98, f"{SHORT.get(g, U.SUB_LABEL.get(g, g))} mean ", rotation=90, va="top", ha="right", fontsize=7,
                    color=U.INK2, transform=ax.get_xaxis_transform())
        ax.set(title=f"{m}{' (headline)' if m == headline else ' (sensitivity)'}",
               xlabel="Starting Jun-Sep rainfall R (mm); deficit takes it to R - 100")
    axes[0].set_ylabel("Yield change for a 100 mm deficit (%), T fixed")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle("100 mm deficit across the observed rainfall range (T at panel mean)", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'range_curve'))}")

    d = tab[(tab.level == "district") & (tab.model == headline) & (tab.scenario == "deficit_100mm")]
    order = dm.assign(o=dm.subdivision.map({s: i for i, s in enumerate(U.SUB_ORDER)})).sort_values(["o", "R_season"]).district.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, col, unit in [(axes[0], "pct", "%"), (axes[1], "kgha", "kg/ha")]:
        for off, var, mk, colr, lab in [(-0.15, "A", "o", "#2a78d6", "A: T fixed (headline)"),
                                        (0.15, "B", "s", "#eb6834", "B: T moves with R (exploratory)")]:
            q = d[d.variant == var].set_index("unit").loc[order]
            y = np.arange(len(order)) + off
            sc = 100 if col == "pct" else 1
            ax.errorbar(sc * q[col], y, xerr=[sc * (q[col] - q[f"{col}_lo_{HEAD}"]), sc * (q[f"{col}_hi_{HEAD}"] - q[col])],
                        fmt=mk, color=colr, ms=5, lw=1, capsize=0, label=lab)
        ax.axvline(0, color=U.INK2, lw=1)
        ax.set_yticks(np.arange(len(order)), [f"{o} ({U.SUB_LABEL.get(dm.set_index('district').subdivision[o], '')})" for o in order])
        ax.set(xlabel=f"Change for a 100 mm deficit ({unit})")
    axes[0].set_title("Percent (headline unit)")
    axes[1].set_title("kg/ha (baseline: district mean observed yield)")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle(f"100 mm deficit at each district's mean rainfall, {headline}, 95% moving-block bootstrap",
                 fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'district_effects'))}")
    out.log("Results are associations under the model's assumptions, not causal effects.")
    out.close()


if __name__ == "__main__":
    main()
