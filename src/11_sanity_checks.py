"""Step 11: sanity checks of the final results (SPEC A14.5).

Usage: python src/11_sanity_checks.py <panel.csv> <outdir>      (after src/06 and src/08)
(a) Recompute the 100 mm effects independently with numpy from the STORED coefficients
    (06_models_coefficients.csv) and centring constants (06_models_centring_constants.csv) and the panel's
    district means; compare with 08_scenario_results.csv (state rows, variant A). No pipeline_utils model code.
(b) Turning points of R and T in M2, share of observations on each side, within-district SD of R and T.
(c) Response curves of ln(yield) relative to the district's mean weather, vs rainfall (T at the district
    mean) and vs temperature (R at the district mean), for the driest, median and wettest district by mean
    R_season; M2 with a 95% moving-block band (L = 3), M1 dashed; rug of the district's observed values.
(d) Symmetry: 100 mm surplus vs 100 mm deficit for M1 and M2 (08 rows and the independent recomputation).
"""
import numpy as np
import pandas as pd

import pipeline_utils as U
import config as C  # noqa: E402


def lp(b: dict, c: dict, R, T) -> np.ndarray:
    """Independent implementation of the weather part of the linear predictor."""
    rc = (np.asarray(R, float) - c["R_season"]) / 100.0
    tc = np.asarray(T, float) - c["T_season"]
    return (b.get("Rc", 0) * rc + b.get("Rc_sq", 0) * rc ** 2 + b.get("Tc", 0) * tc + b.get("Tc_sq", 0) * tc ** 2)


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    out = U.Outputs(a.outdir, "11_sanity", a.panel)
    plt = U.setup_matplotlib()
    tdir = a.outdir / "tables"
    coef = pd.read_csv(tdir / "06_models_coefficients.csv", comment="#")
    cst = pd.read_csv(tdir / "06_models_centring_constants.csv", comment="#").iloc[0].to_dict()
    res = pd.read_csv(tdir / "08_scenario_results.csv", comment="#")
    raw = pd.read_csv(a.panel)
    B = {m: dict(zip(coef[coef.model == m].term, coef[coef.model == m].coef)) for m in ["M1", "M2"]}
    dm = raw.groupby("district")[["R_season", "T_season", "yield_kgha"]].mean()

    # (a) + (d)
    rows = []
    for m in ["M1", "M2"]:
        for sc, dR in [("deficit_100mm", -100.0), ("surplus_100mm", +100.0)]:
            d = lp(B[m], cst, dm.R_season + dR, dm.T_season) - lp(B[m], cst, dm.R_season, dm.T_season)
            pct = float(np.mean(np.exp(d) - 1))
            kg = float(np.mean((np.exp(d) - 1) * dm.yield_kgha))
            r08 = res[(res.level == "state") & (res.model == m) & (res.scenario == sc) & (res.variant == "A")].iloc[0]
            rows.append({"model": m, "scenario": sc, "pct_numpy": pct, "pct_src08": r08.pct, "abs_diff_pct": abs(pct - r08.pct),
                         "kgha_numpy": kg, "kgha_src08": r08.kgha, "abs_diff_kgha": abs(kg - r08.kgha),
                         "ci_lo_src08": r08.pct_lo_L3, "ci_hi_src08": r08.pct_hi_L3})
    chk = pd.DataFrame(rows)
    ok = bool((chk.abs_diff_pct < 1e-9).all() and (chk.abs_diff_kgha < 1e-6).all())
    out.log("(a) Independent numpy recomputation vs src/08 (state mean, T fixed):")
    out.log(chk.to_string(index=False, float_format=lambda x: f"{x:.6g}"))
    out.log(f"    -> {'PASS' if ok else 'FAIL'}: max |diff| pct {chk.abs_diff_pct.max():.2e}, kg/ha {chk.abs_diff_kgha.max():.2e}")
    sym = chk.pivot(index="model", columns="scenario", values="pct_numpy")
    sym["sum_surplus_plus_deficit"] = sym.surplus_100mm + sym.deficit_100mm
    sym["ratio_abs_surplus_to_abs_deficit"] = sym.surplus_100mm.abs() / sym.deficit_100mm.abs()
    out.log("\n(d) Symmetry (a symmetric response would give sum 0 and ratio 1; the log link alone makes the surplus "
            "slightly LARGER in absolute value than the deficit for a linear model, since exp(b) - 1 > |exp(-b) - 1|):")
    out.log(sym.reset_index().to_string(index=False, float_format=lambda x: f"{x:+.5f}"))

    # (b) turning points
    b2 = B["M2"]
    Rstar = cst["R_season"] + 100 * (-b2["Rc"] / (2 * b2["Rc_sq"]))
    Tstar = cst["T_season"] - b2["Tc"] / (2 * b2["Tc_sq"])
    wR = raw.R_season - raw.groupby("district").R_season.transform("mean")
    wT = raw.T_season - raw.groupby("district").T_season.transform("mean")
    tp = pd.DataFrame([
        {"variable": "R_season (mm)", "turning_point": Rstar, "shape": "maximum" if b2["Rc_sq"] < 0 else "minimum",
         "share_obs_below": float((raw.R_season < Rstar).mean()), "share_obs_above": float((raw.R_season >= Rstar).mean()),
         "within_district_sd_pooled": float(wR.std()), "mean_of_district_sds": float(raw.groupby("district").R_season.std().mean()),
         "observed_min": raw.R_season.min(), "observed_max": raw.R_season.max(),
         "districts_with_mean_above_tp": ", ".join(dm.index[dm.R_season > Rstar])},
        {"variable": "T_season (deg C)", "turning_point": Tstar, "shape": "maximum" if b2["Tc_sq"] < 0 else "minimum",
         "share_obs_below": float((raw.T_season < Tstar).mean()), "share_obs_above": float((raw.T_season >= Tstar).mean()),
         "within_district_sd_pooled": float(wT.std()), "mean_of_district_sds": float(raw.groupby("district").T_season.std().mean()),
         "observed_min": raw.T_season.min(), "observed_max": raw.T_season.max(),
         "districts_with_mean_above_tp": ", ".join(dm.index[dm.T_season > Tstar])}])
    out.log("\n(b) Turning points (M2), observations on each side, within-district SD:")
    out.log(tp.T.to_string(header=False))

    # (c) response curves with MBB band for M2
    p = U.load_panel(a.panel)
    fe = U.FastFE(p, "ln_yield", U.MODELS["M2"]["rain"])
    assert np.allclose(fe.fit(np.arange(len(p))), [B["M2"][k] for k in fe.cols], rtol=1e-7)
    years, yrows = U.year_rows(p)
    bs = [dict(zip(fe.cols, fe.fit(U.rows_from_year_draw(yrows, d))))
          for d in U.block_draws(len(years), C.BLOCK_LENGTH, C.N_BOOT_BLOCK, C.BOOT_SEEDS[f"block_L{C.BLOCK_LENGTH}"])]
    order = dm.sort_values("R_season").index.tolist()
    picks = {"dry": order[0], "median": order[len(order) // 2], "wet": order[-1]}
    Rg = np.linspace(raw.R_season.min(), raw.R_season.max(), 80)
    Tg = np.linspace(raw.T_season.min(), raw.T_season.max(), 80)
    crow = []
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey="row")
    for j, (lab, d) in enumerate(picks.items()):
        Rb, Tb = dm.loc[d, "R_season"], dm.loc[d, "T_season"]
        obs = raw[raw.district == d]
        for i, (grid, var) in enumerate([(Rg, "R"), (Tg, "T")]):
            f = (lambda b, g: lp(b, cst, g, Tb) - lp(b, cst, Rb, Tb)) if var == "R" else \
                (lambda b, g: lp(b, cst, Rb, g) - lp(b, cst, Rb, Tb))
            m2 = f(B["M2"], grid)
            band = np.array([f(b, grid) for b in bs])
            lo, hi = np.percentile(band, 2.5, axis=0), np.percentile(band, 97.5, axis=0)
            m1 = f(B["M1"], grid)
            ax = axes[i, j]
            ax.fill_between(grid, lo, hi, color="#86b6ef", alpha=0.45, lw=0, label="M2 95% MBB band (L=3)")
            ax.plot(grid, m2, color="#1c5cab", lw=2, label="M2 (headline)")
            ax.plot(grid, m1, color=U.INK2, lw=1.2, ls="--", label="M1")
            ax.axhline(0, color=U.INK, lw=0.8)
            vals = obs.R_season if var == "R" else obs.T_season
            ymin = ax.get_ylim()[0]
            ax.plot(vals, np.full(len(vals), 0), "|", color=U.INK, ms=12, transform=ax.get_xaxis_transform(),
                    label="observed (district)")
            ax.axvline(Rb if var == "R" else Tb, color=U.MUTED, lw=1, ls=":")
            ax.set(xlabel="Jun-Sep rainfall (mm)" if var == "R" else "Jun-Sep mean temperature (deg C)")
            if i == 0:
                ax.set_title(f"{lab}: {d}\nmean R {Rb:.0f} mm, mean T {Tb:.1f} deg C")
            for g_, a_, l_, h_, b1 in zip(grid, m2, lo, hi, m1):
                crow.append({"district": d, "type": lab, "axis": var, "x": g_, "M2": a_, "M2_lo": l_, "M2_hi": h_, "M1": b1})
    axes[0, 0].set_ylabel("Change in ln(yield) vs district mean weather\n(T at district mean)")
    axes[1, 0].set_ylabel("Change in ln(yield) vs district mean weather\n(R at district mean)")
    axes[0, 2].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.suptitle("Response curves for the driest, median and wettest district (rug = observed years)", fontweight="bold", y=1.0)
    out.log(f"\n(c) Response-curve districts: {picks}")
    out.log(f"figure -> {U.rel(out.figure(fig, 'response_curves'))}")
    for df, nm in [(chk, "headline_recompute"), (sym.reset_index(), "symmetry"), (tp, "turning_points"),
                   (pd.DataFrame(crow), "response_curves")]:
        out.log(f"table -> {U.rel(out.table(df, nm))}")
    out.close()
    if not ok:
        raise SystemExit("FAIL: independent recomputation differs from src/08")


if __name__ == "__main__":
    main()
