"""Step 8: 100 mm deficit scenario (and illustrative weak-monsoon scenarios).

Usage: python src/08_scenario_100mm.py <panel.csv> <outdir>

Effect of a rainfall change from R_old to R_new: delta = f(R_new) - f(R_old), f = fitted rainfall part.
  ln-yield models : pct = exp(delta) - 1;  kg/ha = pct * Ybar_d
  kg/ha models    : kg/ha = delta;         pct = delta / Ybar_d
Rbar_d = district mean rainfall over the panel years; Ybar_d = district mean observed yield.

Scenarios
- deficit_100mm           R_season: Rbar_d -> Rbar_d - 100 (headline linear/quadratic; kg/ha models)
- weak_monsoon_90/80pct   R_season: Rbar_d -> 0.9 / 0.8 x Rbar_d   (ILLUSTRATIVE)
- timing models (SPEC A3): deficit_100mm_split (proportional to each window's share of Rbar_season,d)
  = main timing scenario; deficit_100mm_early_only / _late_only = sensitivity. timing_quad = exploratory.
- across the observed range: 100 mm deficit from R to R-100 for R in [min+100, max] of R_season,
  so both points lie inside the observed range.

Intervals: 95% percentile bootstrap, resampling years (main) and resampling districts (check);
N_BOOT reps each, seeds from config.SEED. Rbar_d and Ybar_d are held at sample values; only the
coefficients vary across replications. Subdivision/state rows = unweighted mean of district rows.
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402  (pipeline_utils puts the repo root on sys.path)

SHORT = {"MADHYA MAHARASHTRA": "Madhya M."}  # figure labels only
RSEASON_MODELS = ["linear", "quadratic", "linear_level", "quadratic_level"]
TIMING_MODELS = ["timing_linear", "timing_quad"]


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
    res = {}
    for m, s, _, ch in scen:
        res[(m, s)] = U.effect(params[m], U.MODELS[m]["outcome"], ch, ybar)
    return res


def range_curve(params: dict, grid: np.ndarray, ybar_all: float) -> dict:
    return {m: U.effect(params[m], U.MODELS[m]["outcome"], {"R_season": (grid, grid - C.RAIN_SHOCK_MM)}, ybar_all)
            for m in RSEASON_MODELS}


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "08_scenario", a.panel)
    plt = U.setup_matplotlib()
    p = U.load_panel(a.panel)
    out.log(f"Panel: {U.describe_panel(p)}")
    models = RSEASON_MODELS + TIMING_MODELS

    dm = p.groupby("district").agg(subdivision=("subdivision", "first"), R_season=("R_season", "mean"),
                                   R_early=("R_early", "mean"), R_late=("R_late", "mean"),
                                   Ybar_kgha=("yield_kgha", "mean")).reset_index()
    assert np.allclose(dm.R_early + dm.R_late, dm.R_season), "Jun-Jul + Aug-Sep must equal Jun-Sep"
    ybar = dm.Ybar_kgha.to_numpy()
    scen = scenarios(dm)
    dm["share_early"] = dm.R_early / dm.R_season
    out.log("District means used (Rbar in mm, Ybar in kg/ha), and the early-window share of the 100 mm split:")
    out.log(dm.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Point estimates (PanelOLS) and agreement with the fast within estimator used in the bootstrap.
    point = {}
    for m in models:
        spec = U.MODELS[m]
        res = U.fit_fe(p, spec["outcome"], spec["rain"])
        fast = U.fe_params_fast(p, spec["outcome"], spec["rain"])
        assert np.allclose(res.params[fast.index], fast, rtol=1e-7, atol=1e-12), f"fast estimator mismatch {m}"
        point[m] = res.params
    pe = all_effects(point, scen, ybar)
    rmin, rmax = p.R_season.min(), p.R_season.max()
    grid = np.linspace(rmin + C.RAIN_SHOCK_MM, rmax, C.RANGE_GRID_POINTS)
    ybar_all = p.yield_kgha.mean()
    pc = range_curve(point, grid, ybar_all)

    # Bootstraps
    ss = np.random.SeedSequence(C.SEED).spawn(2)
    boot = {}
    for kind, rng, resample in [("years", np.random.default_rng(ss[0]), U.resample_years),
                                ("districts", np.random.default_rng(ss[1]), U.resample_districts)]:
        eff = {k: ([], []) for k in pe}
        curve = {m: ([], []) for m in RSEASON_MODELS}
        for b in range(C.N_BOOT):
            bd = resample(p, rng)
            prm = {m: U.fe_params_fast(bd, U.MODELS[m]["outcome"], U.MODELS[m]["rain"]) for m in models}
            for k, (pct, kg) in all_effects(prm, scen, ybar).items():
                eff[k][0].append(pct)
                eff[k][1].append(kg)
            for m, (pct, kg) in range_curve(prm, grid, ybar_all).items():
                curve[m][0].append(pct)
                curve[m][1].append(kg)
        boot[kind] = ({k: (np.array(v[0]), np.array(v[1])) for k, v in eff.items()},
                      {m: (np.array(v[0]), np.array(v[1])) for m, v in curve.items()})
        out.log(f"Bootstrap over {kind}: {C.N_BOOT} reps done")

    def ci(arr):
        return np.nanpercentile(arr, 2.5, axis=0), np.nanpercentile(arr, 97.5, axis=0)

    # District rows
    rows = []
    for (m, s, lab, _) in scen:
        pct, kg = pe[(m, s)]
        r = {"model": m, "role": U.MODELS[m]["role"], "scenario": s, "label": lab}
        by = {kind: boot[kind][0][(m, s)] for kind in boot}
        lo_y, hi_y = ci(by["years"][0]); klo_y, khi_y = ci(by["years"][1])
        lo_d, hi_d = ci(by["districts"][0]); klo_d, khi_d = ci(by["districts"][1])
        for i, d in dm.iterrows():
            rows.append({**r, "level": "district", "unit": d.district, "subdivision": d.subdivision,
                         "Rbar_season_mm": d.R_season, "Ybar_kgha": d.Ybar_kgha,
                         "pct": pct[i], "pct_lo_years": lo_y[i], "pct_hi_years": hi_y[i],
                         "pct_lo_districts": lo_d[i], "pct_hi_districts": hi_d[i],
                         "kgha": kg[i], "kgha_lo_years": klo_y[i], "kgha_hi_years": khi_y[i],
                         "kgha_lo_districts": klo_d[i], "kgha_hi_districts": khi_d[i]})
        # Aggregates: unweighted mean of districts, computed inside each replication.
        groups = [(s_, (dm.subdivision == s_).to_numpy()) for s_ in sorted(dm.subdivision.unique())]
        groups.append(("ALL DISTRICTS", np.ones(len(dm), bool)))
        for g, k in groups:
            agg = lambda x: x[..., k].mean(axis=-1)  # noqa: E731
            a_lo_y, a_hi_y = ci(agg(by["years"][0])); ak_lo_y, ak_hi_y = ci(agg(by["years"][1]))
            a_lo_d, a_hi_d = ci(agg(by["districts"][0])); ak_lo_d, ak_hi_d = ci(agg(by["districts"][1]))
            rows.append({**r, "level": "subdivision" if g != "ALL DISTRICTS" else "state", "unit": g,
                         "subdivision": g, "Rbar_season_mm": dm.R_season[k].mean(), "Ybar_kgha": dm.Ybar_kgha[k].mean(),
                         "pct": pct[k].mean(), "pct_lo_years": a_lo_y, "pct_hi_years": a_hi_y,
                         "pct_lo_districts": a_lo_d, "pct_hi_districts": a_hi_d,
                         "kgha": kg[k].mean(), "kgha_lo_years": ak_lo_y, "kgha_hi_years": ak_hi_y,
                         "kgha_lo_districts": ak_lo_d, "kgha_hi_districts": ak_hi_d})
    tab = pd.DataFrame(rows)

    def fmt(df):
        d = df.copy()
        d["pct [years CI] {districts CI}"] = [
            f"{100 * r.pct:+6.1f}% [{100 * r.pct_lo_years:+.1f}, {100 * r.pct_hi_years:+.1f}] "
            f"{{{100 * r.pct_lo_districts:+.1f}, {100 * r.pct_hi_districts:+.1f}}}" for r in d.itertuples()]
        d["kg/ha [years CI]"] = [f"{r.kgha:+7.1f} [{r.kgha_lo_years:+.1f}, {r.kgha_hi_years:+.1f}]" for r in d.itertuples()]
        return d[["model", "scenario", "label", "unit", "Rbar_season_mm", "pct [years CI] {districts CI}", "kg/ha [years CI]"]]

    out.log("\nSCENARIO RESULTS - subdivision and state rows (unweighted means of districts).")
    out.log("Brackets: 95% bootstrap over years [..] and over districts {..}.")
    agg_tab = tab[tab.level != "district"]
    out.log(fmt(agg_tab).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    out.log("\nSCENARIO RESULTS - districts, headline models, 100 mm deficit:")
    out.log(fmt(tab[(tab.level == "district") & tab.model.isin(["linear", "quadratic"]) &
                    (tab.scenario == "deficit_100mm")]).to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    out.log("\nWeak-monsoon rows are ILLUSTRATIVE: they apply the fitted curve to a uniform percentage cut.")

    # Range curve table
    crow = []
    for m in RSEASON_MODELS:
        pct, kg = pc[m]
        by, bd_ = boot["years"][1][m], boot["districts"][1][m]
        lo, hi = ci(by[0]); klo, khi = ci(by[1]); dlo, dhi = ci(bd_[0])
        for j, R in enumerate(grid):
            crow.append({"model": m, "R_from_mm": R, "R_to_mm": R - C.RAIN_SHOCK_MM, "pct": pct[j],
                         "pct_lo_years": lo[j], "pct_hi_years": hi[j], "pct_lo_districts": dlo[j],
                         "pct_hi_districts": dhi[j], "kgha_at_panel_mean_yield": kg[j], "kgha_lo_years": klo[j],
                         "kgha_hi_years": khi[j], "panel_mean_yield_kgha": ybar_all})
    curve_tab = pd.DataFrame(crow)
    out.log(f"\nAcross the observed range (R from {grid[0]:.0f} to {grid[-1]:.0f} mm), 100 mm deficit, "
            f"kg/ha at the panel mean yield {ybar_all:.0f} kg/ha:")
    show = curve_tab[curve_tab.R_from_mm.isin(grid[[0, len(grid) // 4, len(grid) // 2, 3 * len(grid) // 4, -1]])]
    out.log(show[["model", "R_from_mm", "pct", "pct_lo_years", "pct_hi_years", "kgha_at_panel_mean_yield"]]
            .to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    for df, nm in [(tab, "results"), (curve_tab, "range_curve"), (dm, "district_means")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")

    # Figures
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, m, title in [(axes[0], "linear", "Linear in R_season"), (axes[1], "quadratic", "Quadratic in R_season")]:
        c = curve_tab[curve_tab.model == m]
        ax.fill_between(c.R_from_mm, 100 * c.pct_lo_years, 100 * c.pct_hi_years, color="#86b6ef", alpha=0.45,
                        lw=0, label="95% bootstrap (years)")
        ax.plot(c.R_from_mm, 100 * c.pct_lo_districts, color=U.MUTED, lw=1, ls=":", label="95% bootstrap (districts)")
        ax.plot(c.R_from_mm, 100 * c.pct_hi_districts, color=U.MUTED, lw=1, ls=":")
        ax.plot(c.R_from_mm, 100 * c.pct, color="#1c5cab", lw=2, label="Point estimate")
        ax.axhline(0, color=U.INK2, lw=1)
        for s_ in sorted(dm.subdivision.unique()):
            r_ = dm.R_season[dm.subdivision == s_].mean()
            ax.axvline(r_, color=U.SUB_COLOR.get(s_, U.MUTED), lw=1, ls="--")
            ax.text(r_, 0.98, f"{SHORT.get(s_, U.SUB_LABEL.get(s_, s_))} mean ", rotation=90, va="top", ha="right", fontsize=7,
                    color=U.INK2, transform=ax.get_xaxis_transform())
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
            ax.errorbar(sc * q[col], y, xerr=[sc * (q[col] - q[f"{col}_lo_years"]), sc * (q[f"{col}_hi_years"] - q[col])],
                        fmt=mk, color=colr, ms=5, lw=1, capsize=0, label=m)
        ax.axvline(0, color=U.INK2, lw=1)
        ax.set_yticks(np.arange(len(order)), [f"{o} ({U.SUB_LABEL.get(dm.set_index('district').subdivision[o], '')})" for o in order])
        ax.set(xlabel=f"Change for a 100 mm deficit ({unit})")
    axes[0].set_title("Percent (ln-yield models)")
    axes[1].set_title("kg/ha (= percent x district mean yield)")
    axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle("100 mm deficit at each district's mean rainfall, 95% year-bootstrap interval", fontweight="bold", y=1.02)
    out.log(f"figure -> {U.rel(out.figure(fig, 'district_effects'))}")
    out.log("Results are associations under the model's assumptions, not causal effects.")
    out.close()


if __name__ == "__main__":
    main()
