"""Step 8: 100 mm deficit scenario (and illustrative weak-monsoon scenarios).

Usage: python src/08_scenario_100mm.py <panel.csv> <outdir>

Effect of a rainfall change from R_old to R_new: delta = f(R_new) - f(R_old), f = fitted rainfall part.
  ln-yield models : pct = exp(delta) - 1;  kg/ha = pct * Ybar_d
  kg/ha models    : kg/ha = delta;         pct = delta / Ybar_d
Rbar_d = district mean rainfall over the panel years. Ybar_d = KG/HA BASELINE = district mean observed
yield over the panel years (SPEC A9). Percent is the headline unit. No smearing is needed for the
percent effect (a constant smearing factor cancels in the ratio), and Ybar_d is observed, not predicted.

Scenarios
- deficit_100mm           R_season: Rbar_d -> Rbar_d - 100 (headline linear/quadratic; kg/ha models)
- weak_monsoon_90/80pct   R_season: Rbar_d -> 0.9 / 0.8 x Rbar_d   (ILLUSTRATIVE)
- timing models (SPEC A3): deficit_100mm_split (proportional to each window's share of Rbar_season,d)
  = main timing scenario; deficit_100mm_early_only / _late_only = sensitivity. timing_quad = exploratory.
- across the observed range: 100 mm deficit from R to R-100 for R in [min+100, max] of R_season,
  so both points lie inside the observed range.

Intervals (SPEC A7): 95% percentile intervals from the moving-block bootstrap over years, L = BLOCK_LENGTH
(headline) and BLOCK_LENGTH_SENSITIVITY; plus the district bootstrap as a check. N_BOOT_BLOCK reps each;
seeds config.BOOT_SEEDS (the same year draws as src/06). The full model is refitted in every replication.
Rbar_d and Ybar_d are held at sample values. Subdivision/state rows = unweighted mean of district rows.
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402  (pipeline_utils puts the repo root on sys.path)

SHORT = {"MADHYA MAHARASHTRA": "Madhya M."}  # figure labels only
RSEASON_MODELS = ["linear", "quadratic", "linear_level", "quadratic_level"]
TIMING_MODELS = ["timing_linear", "timing_quad"]
BASELINE_NOTE = "kg/ha baseline = district mean observed yield over the panel years"
HEAD = f"L{C.BLOCK_LENGTH}"


def scenarios(dm: pd.DataFrame) -> list:
    """(model, scenario, label, changes) with per-district arrays."""
    Rs, Re, Rl = dm.R_season.to_numpy(), dm.R_early.to_numpy(), dm.R_late.to_numpy()
    out = []
    for m in RSEASON_MODELS:
        out.append((m, "deficit_100mm", "main", {"R_season": (Rs, Rs - C.RAIN_SHOCK_MM)}))
        for fr in C.WEAK_MONSOON_FRACTIONS:
            out.append((m, f"weak_monsoon_{round(100 * fr)}pct", "ILLUSTRATIVE", {"R_season": (Rs, fr * Rs)}))
    de = C.RAIN_SHOCK_MM * Re / Rs
    dl = C.RAIN_SHOCK_MM - de
    for m in TIMING_MODELS:
        lab = "main timing scenario" if m == "timing_linear" else "EXPLORATORY model"
        out.append((m, "deficit_100mm_split", lab, {"R_early": (Re, Re - de), "R_late": (Rl, Rl - dl)}))
        out.append((m, "deficit_100mm_early_only", "sensitivity", {"R_early": (Re, Re - C.RAIN_SHOCK_MM)}))
        out.append((m, "deficit_100mm_late_only", "sensitivity", {"R_late": (Rl, Rl - C.RAIN_SHOCK_MM)}))
    return out


def all_effects(params: dict, scen: list, ybar: np.ndarray) -> dict:
    return {(m, s): U.effect(params[m], U.MODELS[m]["outcome"], ch, ybar) for m, s, _, ch in scen}


def range_curve(params: dict, grid: np.ndarray, ybar_all: float) -> dict:
    return {m: U.effect(params[m], U.MODELS[m]["outcome"], {"R_season": (grid, grid - C.RAIN_SHOCK_MM)}, ybar_all)
            for m in RSEASON_MODELS}


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "08_scenario", a.panel)
    plt = U.setup_matplotlib()
    p = U.load_panel(a.panel)
    out.log(f"Panel: {U.describe_panel(p)}")
    out.log(f"Percent is the headline unit; {BASELINE_NOTE}.")
    models = RSEASON_MODELS + TIMING_MODELS

    dm = p.groupby("district").agg(subdivision=("subdivision", "first"), R_season=("R_season", "mean"),
                                   R_early=("R_early", "mean"), R_late=("R_late", "mean"),
                                   Ybar_kgha=("yield_kgha", "mean")).reset_index()
    assert np.allclose(dm.R_early + dm.R_late, dm.R_season), "Jun-Jul + Aug-Sep must equal Jun-Sep"
    assert list(dm.district) == list(pd.unique(p.district)), "district order must match the panel order"
    ybar = dm.Ybar_kgha.to_numpy()
    scen = scenarios(dm)
    dm["share_early"] = dm.R_early / dm.R_season
    out.log("District means used (Rbar in mm, Ybar = kg/ha baseline), and the early-window share of the split:")
    out.log(dm.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    point, fes = {}, {}
    for m in models:
        spec = U.MODELS[m]
        res = U.fit_fe(p, spec["outcome"], spec["rain"])
        fes[m] = U.FastFE(p, spec["outcome"], spec["rain"])
        fast = fes[m].fit(np.arange(len(p)))
        assert np.allclose(res.params[fes[m].cols].to_numpy(), fast, rtol=1e-7, atol=1e-12), f"FastFE mismatch {m}"
        point[m] = res.params
    pe = all_effects(point, scen, ybar)
    grid = np.linspace(p.R_season.min() + C.RAIN_SHOCK_MM, p.R_season.max(), C.RANGE_GRID_POINTS)
    ybar_all = p.yield_kgha.mean()
    pc = range_curve(point, grid, ybar_all)

    # Bootstraps: moving blocks over years (same draws as src/06) and districts (check).
    years, yrows = U.year_rows(p)
    schemes = {f"L{L}": [(U.rows_from_year_draw(yrows, d), None)
                         for d in U.block_draws(len(years), L, C.N_BOOT_BLOCK, C.BOOT_SEEDS[f"block_L{L}"])]
               for L in [C.BLOCK_LENGTH] + list(C.BLOCK_LENGTH_SENSITIVITY)}
    schemes["districts"] = [U.rows_from_district_draw(p, d)
                            for d in U.district_draws(p.district.nunique(), C.N_BOOT_BLOCK, C.BOOT_SEEDS["districts"])]
    boot = {}
    for kind, draws in schemes.items():
        eff = {k: ([], []) for k in pe}
        curve = {m: ([], []) for m in RSEASON_MODELS}
        for rows, codes in draws:
            prm = {m: pd.Series(fes[m].fit(rows, codes), index=fes[m].cols) for m in models}
            for k, (pct, kg) in all_effects(prm, scen, ybar).items():
                eff[k][0].append(pct)
                eff[k][1].append(kg)
            for m, (pct, kg) in range_curve(prm, grid, ybar_all).items():
                curve[m][0].append(pct)
                curve[m][1].append(kg)
        boot[kind] = ({k: (np.array(v[0]), np.array(v[1])) for k, v in eff.items()},
                      {m: (np.array(v[0]), np.array(v[1])) for m, v in curve.items()})
        seed = C.BOOT_SEEDS["districts" if kind == "districts" else f"block_{kind}"]
        out.log(f"Bootstrap {kind}: {len(draws)} reps, seed {seed}")

    def ci(arr):
        return np.nanpercentile(arr, 2.5, axis=0), np.nanpercentile(arr, 97.5, axis=0)

    kinds = list(schemes)
    groups = [(s_, (dm.subdivision == s_).to_numpy()) for s_ in sorted(dm.subdivision.unique())]
    groups.append(("ALL DISTRICTS", np.ones(len(dm), bool)))
    rows = []
    for (m, s, lab, _) in scen:
        pct, kg = pe[(m, s)]
        base = {"model": m, "role": U.MODELS[m]["role"], "scenario": s, "label": lab, "kgha_baseline": BASELINE_NOTE}
        by = {kind: boot[kind][0][(m, s)] for kind in kinds}
        units = [("district", d.district, d.subdivision, np.arange(len(dm)) == i) for i, d in dm.iterrows()]
        units += [("subdivision" if g != "ALL DISTRICTS" else "state", g, g, k) for g, k in groups]
        for level, unit, sub, k in units:
            r = {**base, "level": level, "unit": unit, "subdivision": sub, "Rbar_season_mm": dm.R_season[k].mean(),
                 "Ybar_kgha": dm.Ybar_kgha[k].mean(), "pct": pct[k].mean(), "kgha": kg[k].mean()}
            for kind in kinds:
                lo, hi = ci(by[kind][0][:, k].mean(axis=1))
                klo, khi = ci(by[kind][1][:, k].mean(axis=1))
                r.update({f"pct_lo_{kind}": lo, f"pct_hi_{kind}": hi, f"kgha_lo_{kind}": klo, f"kgha_hi_{kind}": khi})
            rows.append(r)
    tab = pd.DataFrame(rows)

    def fmt(df):
        d = df.copy()
        d[f"pct [MBB {HEAD}] {{districts}}"] = [
            f"{100 * r['pct']:+6.1f}% [{100 * r[f'pct_lo_{HEAD}']:+.1f}, {100 * r[f'pct_hi_{HEAD}']:+.1f}] "
            f"{{{100 * r['pct_lo_districts']:+.1f}, {100 * r['pct_hi_districts']:+.1f}}}" for _, r in d.iterrows()]
        for L in C.BLOCK_LENGTH_SENSITIVITY:
            d[f"MBB L{L}"] = [f"[{100 * r[f'pct_lo_L{L}']:+.1f}, {100 * r[f'pct_hi_L{L}']:+.1f}]" for _, r in d.iterrows()]
        d[f"kg/ha [MBB {HEAD}]"] = [f"{r['kgha']:+7.1f} [{r[f'kgha_lo_{HEAD}']:+.1f}, {r[f'kgha_hi_{HEAD}']:+.1f}]"
                                     for _, r in d.iterrows()]
        return d[["model", "scenario", "label", "unit", "Rbar_season_mm", f"pct [MBB {HEAD}] {{districts}}"]
                 + [f"MBB L{L}" for L in C.BLOCK_LENGTH_SENSITIVITY] + [f"kg/ha [MBB {HEAD}]"]]

    out.log(f"\nSCENARIO RESULTS - subdivision and state rows (unweighted means of districts); {BASELINE_NOTE}.")
    out.log(f"Brackets: 95% moving-block bootstrap over years, L = {C.BLOCK_LENGTH} [..] (headline); district "
            f"bootstrap {{..}} (check); L = {C.BLOCK_LENGTH_SENSITIVITY} as sensitivity.")
    out.log(fmt(tab[tab.level != "district"]).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    out.log(f"\nSCENARIO RESULTS - districts, headline models, 100 mm deficit ({BASELINE_NOTE}):")
    out.log(fmt(tab[(tab.level == "district") & tab.model.isin(["linear", "quadratic"]) &
                    (tab.scenario == "deficit_100mm")]).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    out.log("\nWeak-monsoon rows are ILLUSTRATIVE: they apply the fitted curve to a uniform percentage cut.")

    crow = []
    for m in RSEASON_MODELS:
        pct, kg = pc[m]
        for j, R in enumerate(grid):
            r = {"model": m, "R_from_mm": R, "R_to_mm": R - C.RAIN_SHOCK_MM, "pct": pct[j],
                 "kgha_at_panel_mean_yield": kg[j], "panel_mean_yield_kgha": ybar_all,
                 "kgha_baseline": "panel mean observed yield (range curve only)"}
            for kind in kinds:
                cp, ck = boot[kind][1][m]
                lo, hi = ci(cp[:, j])
                klo, khi = ci(ck[:, j])
                r.update({f"pct_lo_{kind}": lo, f"pct_hi_{kind}": hi, f"kgha_lo_{kind}": klo, f"kgha_hi_{kind}": khi})
            crow.append(r)
    curve_tab = pd.DataFrame(crow)
    out.log(f"\nAcross the observed range (R from {grid[0]:.0f} to {grid[-1]:.0f} mm), 100 mm deficit; kg/ha at the "
            f"panel mean observed yield {ybar_all:.0f} kg/ha:")
    sel = grid[[0, len(grid) // 4, len(grid) // 2, 3 * len(grid) // 4, -1]]
    out.log(curve_tab[curve_tab.R_from_mm.isin(sel)][["model", "R_from_mm", "pct", f"pct_lo_{HEAD}", f"pct_hi_{HEAD}",
                                                      "kgha_at_panel_mean_yield"]]
            .to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    for df, nm in [(tab, "results"), (curve_tab, "range_curve"), (dm, "district_means")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")

    # Figures
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, m, title in [(axes[0], "linear", "Linear in R_season"), (axes[1], "quadratic", "Quadratic in R_season")]:
        c = curve_tab[curve_tab.model == m]
        ax.fill_between(c.R_from_mm, 100 * c[f"pct_lo_{HEAD}"], 100 * c[f"pct_hi_{HEAD}"], color="#86b6ef", alpha=0.45,
                        lw=0, label=f"95% moving-block bootstrap (years, L={C.BLOCK_LENGTH})")
        ax.plot(c.R_from_mm, 100 * c.pct_lo_districts, color=U.MUTED, lw=1, ls=":", label="95% bootstrap (districts)")
        ax.plot(c.R_from_mm, 100 * c.pct_hi_districts, color=U.MUTED, lw=1, ls=":")
        ax.plot(c.R_from_mm, 100 * c.pct, color="#1c5cab", lw=2, label="Point estimate")
        ax.axhline(0, color=U.INK2, lw=1)
        for s_ in sorted(dm.subdivision.unique()):
            r_ = dm.R_season[dm.subdivision == s_].mean()
            ax.axvline(r_, color=U.SUB_COLOR.get(s_, U.MUTED), lw=1, ls="--")
            ax.text(r_, 0.98, f"{SHORT.get(s_, U.SUB_LABEL.get(s_, s_))} mean ", rotation=90, va="top", ha="right",
                    fontsize=7, color=U.INK2, transform=ax.get_xaxis_transform())
        ax.set(title=title, xlabel="Starting Jun-Sep rainfall R (mm); deficit takes it to R - 100")
    axes[0].set_ylabel("Yield change for a 100 mm deficit (%)")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle("100 mm deficit effect across the observed rainfall range", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'range_curve'))}")

    d = tab[(tab.level == "district") & (tab.scenario == "deficit_100mm") & tab.model.isin(["linear", "quadratic"])]
    order = dm.assign(o=dm.subdivision.map({s: i for i, s in enumerate(U.SUB_ORDER)})).sort_values(["o", "R_season"]).district.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, col, unit in [(axes[0], "pct", "%"), (axes[1], "kgha", "kg/ha")]:
        for off, m, mk, colr in [(-0.15, "linear", "o", "#2a78d6"), (0.15, "quadratic", "s", "#eb6834")]:
            q = d[d.model == m].set_index("unit").loc[order]
            y = np.arange(len(order)) + off
            sc = 100 if col == "pct" else 1
            ax.errorbar(sc * q[col], y, xerr=[sc * (q[col] - q[f"{col}_lo_{HEAD}"]), sc * (q[f"{col}_hi_{HEAD}"] - q[col])],
                        fmt=mk, color=colr, ms=5, lw=1, capsize=0, label=m)
        ax.axvline(0, color=U.INK2, lw=1)
        ax.set_yticks(np.arange(len(order)), [f"{o} ({U.SUB_LABEL.get(dm.set_index('district').subdivision[o], '')})" for o in order])
        ax.set(xlabel=f"Change for a 100 mm deficit ({unit})")
    axes[0].set_title("Percent (headline)")
    axes[1].set_title("kg/ha (baseline: district mean observed yield)")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle(f"100 mm deficit at each district's mean rainfall, 95% moving-block bootstrap (L={C.BLOCK_LENGTH})",
                 fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'district_effects'))}")
    out.log("Results are associations under the model's assumptions, not causal effects.")
    out.close()


if __name__ == "__main__":
    main()
