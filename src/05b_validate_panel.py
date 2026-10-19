"""Step 5b: validate the gridded panel (panel_final.csv) before any model. Descriptive only.

Reads  : config.PANEL_FINAL_FILE, config.OLD_DISTRICT_WEATHER_FILE, config.OLD_DISTRICTS_GPKG,
         config.OLD_TO_CURRENT_FILE, config.BOUNDARY_DIR (current-district areas), config.IMD_SUBDIV_FILE,
         config.DISTRICT_NORMAL_FILE, data/interim/subdivision_rainfall.csv
Writes : outputs/tables/validation_*.csv, outputs/figures/validation_*.png, outputs/logs/05b_validation.txt

(a) gridded vs IMD subdivision R_season, 2000-2015: subdivision series rebuilt as the area-weighted mean
    of all old districts in the subdivision; correlation and mean ratio (gridded / IMD). Also each panel
    district vs its subdivision series. Konkan & Goa includes Goa, which is not in the layer.
(b) old-district mean R_season 2000-2017 vs the district normals (Jun-Sep column), member normals combined
    by area-weighted mean over current-district areas; flag |ratio - 1| > VALIDATION_NORMAL_TOL.
(c) plausibility: T_season range and district ordering, Tmax > Tmin, dry_spell_max range, missing cells and
    nearest-cell fallbacks, maps and bar charts.
(d) corr(R_season, T_season) pooled and within district; VIF of R_season, T_season, dry_spell_max, trend
    on district-demeaned data; cross-district correlation of R_season and the effective number of
    independent rainfall signals: participation ratio (sum l)^2 / sum l^2 of the correlation-matrix
    eigenvalues, and the number of components for 90% of the variance.
(e) descriptive yield vs R_season scatter and mean yield by year, 2000-2017.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import pipeline_utils as U  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("b05", Path(__file__).resolve().parent / "05_build_panel_gridded.py")
B05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B05)

HEAD = "VALIDATION of data/processed/panel_final.csv (IMD gridded data, DataMeet 2011 boundaries). Descriptive; no model."
SEQ_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
SEQ_ORANGE = ["#fde3d6", "#f6b08f", "#eb6834", "#b8461c", "#7a2c0f"]


class Out:
    def __init__(self):
        for d in (C.OUT_TABLES, C.OUT_FIGURES, C.OUT_LOGS):
            d.mkdir(parents=True, exist_ok=True)
        self.f = open(C.OUT_LOGS / "05b_validation.txt", "w")
        self.log("=" * 92); self.log(HEAD); self.log("=" * 92)

    def log(self, *a):
        s = " ".join(str(x) for x in a)
        print(s)
        self.f.write(s + "\n")

    def table(self, df, name):
        p = C.OUT_TABLES / f"validation_{name}.csv"
        with open(p, "w") as f:
            f.write(f"# {HEAD}\n")
            df.to_csv(f, index=False)
        self.log(f"table -> {U.rel(p)}")

    def fig(self, fig, name):
        fig.text(0.01, -0.03, HEAD, fontsize=7, color=U.MUTED, ha="left", va="top")
        p = C.OUT_FIGURES / f"validation_{name}.png"
        fig.savefig(p, bbox_inches="tight", dpi=150)
        import matplotlib.pyplot as plt
        plt.close(fig)
        self.log(f"figure -> {U.rel(p)}")


def main() -> None:
    import geopandas as gpd
    from matplotlib.colors import LinearSegmentedColormap
    plt = U.setup_matplotlib()
    out = Out()
    p = pd.read_csv(C.PANEL_FINAL_FILE)
    wx = pd.read_csv(C.OLD_DISTRICT_WEATHER_FILE)
    old = gpd.read_file(C.OLD_DISTRICTS_GPKG)
    area = old.set_index("district").area_km2
    wx["area_km2"] = wx.district.map(area)
    out.log(f"Panel: {len(p)} rows, {p.district.nunique()} districts, {p.year.min()}-{p.year.max()}; "
            f"weather file: {wx.district.nunique()} old districts")

    # ---- (a) gridded vs IMD subdivision ----
    out.log("\n(a) Gridded R_season vs IMD subdivision totals, 2000-2015")
    sub = pd.read_csv(C.DATA_INTERIM / "subdivision_rainfall.csv")
    w15 = wx[wx.year <= C.YEAR_END_FALLBACK]
    g_sub = w15.groupby(["subdivision", "year"]).apply(
        lambda d: np.average(d.R_season, weights=d.area_km2), include_groups=False).rename("R_grid").reset_index()
    m = g_sub.merge(sub[["subdivision", "year", "R_season"]].rename(columns={"R_season": "R_imd"}),
                    on=["subdivision", "year"])
    ra = m.groupby("subdivision").apply(lambda d: pd.Series({
        "n_years": len(d), "corr": d.R_grid.corr(d.R_imd), "mean_grid_mm": d.R_grid.mean(),
        "mean_imd_mm": d.R_imd.mean(), "mean_ratio_grid_over_imd": d.R_grid.mean() / d.R_imd.mean(),
        "old_districts": ", ".join(sorted(w15[w15.subdivision == d.name].district.unique()))}),
        include_groups=False).reset_index()
    ra["note"] = np.where(ra.subdivision == "KONKAN & GOA", "IMD subdivision includes Goa (not in the layer)", "")
    out.log(ra.drop(columns="old_districts").to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    out.table(ra, "a_subdivision_comparison")
    pd_ = p[p.year <= C.YEAR_END_FALLBACK].merge(sub[["subdivision", "year", "R_season"]].rename(
        columns={"R_season": "R_imd_subdiv"}), on=["subdivision", "year"])
    rd = pd_.groupby(["district", "subdivision"]).apply(lambda d: pd.Series({
        "corr_with_subdivision": d.R_season.corr(d.R_imd_subdiv),
        "mean_ratio_district_over_subdivision": d.R_season.mean() / d.R_imd_subdiv.mean()}),
        include_groups=False).reset_index()
    out.log("Panel districts vs their IMD subdivision series:")
    out.log(rd.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    out.table(rd, "a_district_vs_subdivision")
    subs = [s for s in U.SUB_ORDER if s in set(m.subdivision)]
    from matplotlib.ticker import MaxNLocator
    fig, axes = plt.subplots(1, len(subs), figsize=(4 * len(subs), 3.8))  # own y-axis: Konkan is ~3x wetter
    for ax, s in zip(axes, subs):
        q = m[m.subdivision == s]
        ax.plot(q.year, q.R_imd, color=U.INK2, lw=1.5, ls="--", label="IMD subdivision (CSV)")
        ax.plot(q.year, q.R_grid, color=U.SUB_COLOR[s], marker=U.SUB_MARKER[s], ms=4, label="Gridded (area-weighted)")
        r = ra.set_index("subdivision").loc[s]
        ax.set(title=f"{U.SUB_LABEL[s]}\nr = {r['corr']:.2f}, mean ratio = {r['mean_ratio_grid_over_imd']:.2f}",
               xlabel="Year")
        ax.set_ylim(0, max(q.R_imd.max(), q.R_grid.max()) * 1.08)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
    axes[0].set_ylabel("Jun-Sep rainfall (mm)")
    axes[-1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    if "KONKAN & GOA" in subs:
        axes[subs.index("KONKAN & GOA")].text(0.02, 0.03, "IMD series includes Goa", transform=axes[subs.index("KONKAN & GOA")].transAxes,
                                              fontsize=7, color=U.INK2)
    fig.suptitle("(a) Gridded vs IMD subdivision Jun-Sep rainfall, 2000-2015 (y-axes differ)", fontweight="bold", y=1.06)
    out.fig(fig, "a_subdivision_series")

    # ---- (b) normals ----
    out.log(f"\n(b) Old-district mean R_season {C.YEAR_START}-{C.YEAR_END_TARGET} vs district normals")
    nrm = pd.read_csv(C.DISTRICT_NORMAL_FILE)
    nrm = nrm[nrm.STATE_UT_NAME.str.strip().str.upper() == "MAHARASHTRA"].copy()
    nrm["current_district"] = nrm.DISTRICT.map(B05.canonical)
    xw = pd.read_csv(C.OLD_TO_CURRENT_FILE)
    unmatched = sorted(set(nrm.current_district) - set(xw.current_district))
    if unmatched:
        sys.exit(f"STOP: normals-file districts not matched to the boundary layer: {unmatched}")
    cur = gpd.read_file(C.BOUNDARY_DIR / (Path(C.DATAMEET_LAYER).name + ".shp"))
    cur = cur[cur.ST_NM.str.strip().str.lower() == "maharashtra"].to_crs(C.EQUAL_AREA_CRS)
    cur["current_district"] = cur.DISTRICT.map(B05.canonical)
    cur["cur_area_km2"] = cur.area / 1e6
    nn = nrm.merge(xw[["current_district", "old_icrisat_district"]], on="current_district").merge(
        cur[["current_district", "cur_area_km2"]], on="current_district")
    assert len(nn) == C.EXPECTED_N_CURRENT_DISTRICTS
    nb = nn.groupby("old_icrisat_district").apply(lambda d: pd.Series({
        "normal_jun_sep_mm": np.average(d["Jun-Sep"], weights=d.cur_area_km2),
        "members": " + ".join(d.current_district)}), include_groups=False).reset_index().rename(
        columns={"old_icrisat_district": "district"})
    gm = wx.groupby("district").R_season.mean().rename("grid_mean_2000_2017_mm").reset_index()
    nb = nb.merge(gm, on="district")
    nb["ratio_grid_over_normal"] = nb.grid_mean_2000_2017_mm / nb.normal_jun_sep_mm
    nb["flag_gt_25pct"] = (nb.ratio_grid_over_normal - 1).abs() > C.VALIDATION_NORMAL_TOL
    nb["in_panel"] = nb.district.isin(p.district.unique())
    out.log(nb.sort_values("ratio_grid_over_normal").to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    out.log(f"Flagged (> {100 * C.VALIDATION_NORMAL_TOL:.0f}% off): "
            f"{nb[nb.flag_gt_25pct].district.tolist() or 'none'}; of which in the 13-district panel: "
            f"{nb[nb.flag_gt_25pct & nb.in_panel].district.tolist() or 'none'}. Normal period is not stated in the file.")
    out.table(nb, "b_normals_comparison")

    # ---- (c) plausibility ----
    out.log("\n(c) Plausibility")
    pw = wx[wx.district.isin(p.district.unique())]
    tsum = pw.groupby(["district", "subdivision"]).agg(T_mean=("T_season", "mean"), T_min=("T_season", "min"),
                                                      T_max=("T_season", "max"), Tmax_mean=("Tmax_season", "mean"),
                                                      Tmin_mean=("Tmin_season", "mean"),
                                                      R_mean=("R_season", "mean"), dry_spell_mean=("dry_spell_max", "mean"),
                                                      dry_spell_max=("dry_spell_max", "max")).reset_index()
    tsum = tsum.sort_values("T_mean", ascending=False)
    out.log("Panel districts ordered by mean T_season (deg C):")
    out.log(tsum.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    chk = {"T_season range (deg C)": (p.T_season.min(), p.T_season.max()),
           "all Tmax_season > Tmin_season": bool((wx.Tmax_season > wx.Tmin_season).all()),
           "dry_spell_max range (days)": (int(p.dry_spell_max.min()), int(p.dry_spell_max.max())),
           "R_season range (mm)": (round(p.R_season.min(), 1), round(p.R_season.max(), 1)),
           "R_early + R_late == R_season": bool(np.allclose(p.R_early + p.R_late, p.R_season))}
    for k, v in chk.items():
        out.log(f"  {k}: {v}")
    miss_cols = [c for c in wx.columns if c.startswith(("min_valid_area_share", "nearest_cell_days"))]
    ms = wx.groupby("district")[miss_cols].agg(["min", "max"])
    ms.columns = [f"{a}_{b}" for a, b in ms.columns]
    ms = ms.reset_index()
    out.log("Missing-cell diagnostics per old district (min valid area share over days; nearest-cell fallback days):")
    keep = ["district"] + [c for c in ms.columns if c.endswith("_min") and "share" in c] + \
           [c for c in ms.columns if c.endswith("_max") and "nearest" in c]
    out.log(ms[keep].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    out.table(tsum, "c_plausibility_by_district")
    out.table(ms, "c_missing_cells")
    for col, cmap, lab, nm in [("R_season", SEQ_BLUE, "Mean Jun-Sep rainfall 2000-2017 (mm)", "c_map_rainfall"),
                               ("T_season", SEQ_ORANGE, "Mean Jun-Sep temperature 2000-2017 (deg C)", "c_map_temperature")]:
        mm = old.merge(wx.groupby("district")[col].mean().reset_index(), on="district")
        fig, ax = plt.subplots(figsize=(7.5, 5.5))
        mm.plot(column=col, cmap=LinearSegmentedColormap.from_list("s", cmap), legend=True, ax=ax,
                edgecolor="#fcfcfb", linewidth=0.8, legend_kwds={"label": lab, "shrink": 0.7})
        old[old.district.isin(p.district.unique())].boundary.plot(ax=ax, color=U.INK, linewidth=1.2)
        for r in mm.itertuples():
            pt = r.geometry.representative_point()
            ax.annotate(r.district, (pt.x, pt.y), fontsize=6.5, ha="center", color=U.INK)
        ax.set_axis_off()
        ax.set_title(f"{lab}; old ICRISAT districts (bold outline = 13 panel districts)")
        out.fig(fig, nm)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    order = tsum.sort_values("R_mean").district.tolist()
    for ax, col, colr, xl in [(axes[0], "R_mean", "#2a78d6", "Mean Jun-Sep rainfall (mm)"),
                              (axes[1], "T_mean", "#eb6834", "Mean Jun-Sep temperature (deg C)")]:
        t = tsum.set_index("district").loc[order]
        ax.barh(range(len(order)), t[col], color=colr, height=0.6)
        ax.set_yticks(range(len(order)), [f"{d} ({U.SUB_LABEL[s]})" for d, s in zip(order, t.subdivision)])
        ax.set(xlabel=xl)
        if col == "T_mean":
            ax.set_xlim(t[col].min() - 1, t[col].max() + 0.5)
            ax.text(0.99, 0.01, "axis does not start at zero", transform=ax.transAxes, ha="right", fontsize=7, color=U.INK2)
    fig.suptitle("(c) Panel districts: mean rainfall and temperature, 2000-2017", fontweight="bold", y=1.01)
    out.fig(fig, "c_bars")

    # ---- (d) collinearity and independent rainfall signals ----
    out.log("\n(d) Collinearity and independent rainfall signals (13 panel districts, 2000-2017)")
    dm = p.copy()
    for c in ["R_season", "T_season", "dry_spell_max", "trend", "ln_yield"]:
        dm[f"{c}_w"] = dm[c] - dm.groupby("district")[c].transform("mean")
    r_pooled = p.R_season.corr(p.T_season)
    r_within = dm.R_season_w.corr(dm.T_season_w)
    out.log(f"corr(R_season, T_season): pooled {r_pooled:.3f}; within district {r_within:.3f}")
    Xw = dm[["R_season_w", "T_season_w", "dry_spell_max_w", "trend_w"]].to_numpy()
    vif = []
    for j, nm in enumerate(["R_season", "T_season", "dry_spell_max", "trend"]):
        y, X = Xw[:, j], np.delete(Xw, j, axis=1)
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        r2 = 1 - ((y - X @ b) ** 2).sum() / (y ** 2).sum()
        vif.append({"variable": nm, "within_R2_on_others": r2, "VIF": 1 / (1 - r2)})
    vif2 = []
    X2 = dm[["R_season_w", "T_season_w", "trend_w"]].to_numpy()
    for j, nm in enumerate(["R_season", "T_season", "trend"]):
        y, X = X2[:, j], np.delete(X2, j, axis=1)
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        r2 = 1 - ((y - X @ b) ** 2).sum() / (y ** 2).sum()
        vif2.append({"variable": nm, "within_R2_on_others": r2, "VIF": 1 / (1 - r2)})
    vif = pd.DataFrame(vif).assign(set="R_season, T_season, dry_spell_max, trend")
    vif2 = pd.DataFrame(vif2).assign(set="R_season, T_season, trend")
    vt = pd.concat([vif2, vif])
    out.log("VIF on district-demeaned data:")
    out.log(vt.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    cm = p.pivot(index="year", columns="district", values="R_season").corr()
    lam = np.sort(np.linalg.eigvalsh(cm.to_numpy()))[::-1]
    pr = lam.sum() ** 2 / (lam ** 2).sum()
    k90 = int(np.searchsorted(np.cumsum(lam) / lam.sum(), 0.90) + 1)
    off = cm.to_numpy()[np.triu_indices(len(cm), 1)]
    out.log(f"Cross-district correlation of R_season: mean {off.mean():.3f}, min {off.min():.3f}, max {off.max():.3f}")
    out.log(f"Eigenvalues: {np.round(lam, 3).tolist()}")
    out.log(f"Effective number of independent rainfall signals: participation ratio {pr:.2f}; "
            f"components for 90% of variance: {k90}; first component share {lam[0] / lam.sum():.3f} "
            f"(prototype panel_v1 had exactly 3 distinct series)")
    sig = pd.DataFrame({"component": np.arange(1, len(lam) + 1), "eigenvalue": lam,
                        "share": lam / lam.sum(), "cumulative_share": np.cumsum(lam) / lam.sum()})
    out.table(pd.DataFrame([{"corr_pooled": r_pooled, "corr_within": r_within, "mean_cross_district_corr": off.mean(),
                             "participation_ratio": pr, "components_90pct": k90}]), "d_summary")
    out.table(vt, "d_vif")
    out.table(cm.reset_index(), "d_rainfall_correlation_matrix")
    out.table(sig, "d_rainfall_eigenvalues")
    dorder = p.drop_duplicates("district").assign(o=lambda d: d.subdivision.map({s: i for i, s in enumerate(U.SUB_ORDER)})
                                                  ).sort_values(["o", "district"]).district.tolist()
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    sns.heatmap(cm.loc[dorder, dorder], cmap=LinearSegmentedColormap.from_list("d", ["#1c5cab", "#86b6ef", "#f0efec",
                                                                                        "#ef9a99", "#c0302f"]),
                vmin=-1, vmax=1, annot=True, fmt=".2f", annot_kws={"fontsize": 6.5, "color": U.INK}, square=True,
                linewidths=1, linecolor="#fcfcfb", ax=ax, cbar_kws={"label": "Pearson r across years"})
    ax.set_title(f"(d) Cross-district correlation of Jun-Sep rainfall; effective signals = {pr:.1f}")
    ax.grid(False)
    out.fig(fig, "d_rainfall_correlation")

    # ---- (e) descriptive yield ----
    out.log("\n(e) Descriptive yield, 2000-2017")
    by = p.groupby("year").agg(mean_yield_kgha=("yield_kgha", "mean"), mean_R_season=("R_season", "mean"),
                               mean_T_season=("T_season", "mean")).reset_index()
    out.log(by.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    out.table(by, "e_by_year")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    for s in [x for x in U.SUB_ORDER if x in set(p.subdivision)]:
        q = p[p.subdivision == s]
        axes[0].scatter(q.R_season, q.yield_kgha, s=26, color=U.SUB_COLOR[s], marker=U.SUB_MARKER[s],
                        edgecolor="#fcfcfb", linewidth=0.8, label=U.SUB_LABEL[s])
    late = p[p.year >= 2016]
    axes[0].scatter(late.R_season, late.yield_kgha, s=70, facecolor="none", edgecolor=U.INK, linewidth=1,
                    label="2016-2017 (ring)")
    axes[0].set(title="Yield vs district Jun-Sep rainfall", xlabel="R_season (mm)", ylabel="Yield (kg/ha)")
    axes[0].set_ylim(bottom=0)
    axes[0].legend(frameon=False, fontsize=8)
    bys = p.groupby(["year", "subdivision"]).yield_kgha.mean().unstack()
    axes[1].plot(by.year, by.mean_yield_kgha, color=U.INK, lw=2.5, label="All 13 districts")
    for s in [x for x in U.SUB_ORDER if x in bys.columns]:
        axes[1].plot(bys.index, bys[s], color=U.SUB_COLOR[s], marker=U.SUB_MARKER[s], ms=4, lw=1.4, label=U.SUB_LABEL[s])
    axes[1].axvspan(2015.5, 2017.5, color="#e1e0d9", alpha=0.6, lw=0)
    axes[1].text(2016.5, 0.02, "new\nyears", transform=axes[1].get_xaxis_transform(), ha="center", fontsize=7,
                 color=U.INK2)
    axes[1].set(title="Mean yield by year", xlabel="Year", ylabel="Yield (kg/ha)")
    from matplotlib.ticker import MaxNLocator
    axes[1].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[1].set_ylim(bottom=0)
    axes[1].legend(frameon=False, fontsize=8, ncol=2, loc="lower left")
    fig.suptitle("(e) Descriptive yield, 2000-2017 (no model)", fontweight="bold", y=1.02)
    out.fig(fig, "e_yield")
    out.log(HEAD)
    out.f.close()


if __name__ == "__main__":
    main()
