"""Step 3: exploratory data analysis of a panel (prototype panel_v1.csv or final panel_final.csv).

Usage: python src/03_eda.py <panel.csv> <outdir>
  prototype: python src/03_eda.py data/processed/panel_v1.csv outputs/prototype
  final    : python src/03_eda.py data/processed/panel_final.csv outputs/final
Refuses to write under outputs/final unless the input is panel_final.csv (same guard as src/06-09).
Writes <outdir>/tables/eda_*.csv and <outdir>/figures/eda_*.png. Headers: PROTOTYPE unless final.
(Until 2026-10-19 this script read panel_v1.csv and wrote to outputs/tables and outputs/figures.)

Reads  : config.PANEL_V1_FILE
Writes : outputs/tables/eda_*.csv, outputs/figures/eda_*.png
CSV tables start with a '# PROTOTYPE ...' comment line (read with pandas comment='#').
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
import pipeline_utils as U  # noqa: E402  (same guard and header as src/06-09)

# Palette (reference instance of the dataviz method): first three categorical slots,
# validated all-pairs; markers add a second encoding so identity is not colour-only.
SUB_ORDER = ["VIDARBHA", "MATATHWADA", "MADHYA MAHARASHTRA"]
SUB_LABEL = {"VIDARBHA": "Vidarbha", "MATATHWADA": "Marathwada", "MADHYA MAHARASHTRA": "Madhya Maharashtra"}
SUB_COLOR = dict(zip(SUB_ORDER, ["#2a78d6", "#eb6834", "#1baf7a"]))
SUB_MARKER = dict(zip(SUB_ORDER, ["o", "s", "^"]))
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div", ["#1c5cab", "#86b6ef", "#f0efec", "#ef9a99", "#c0302f"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 11,
    "axes.titleweight": "bold", "font.size": 9, "lines.linewidth": 2, "figure.dpi": 110,
})

VARS = ["ln_yield", "yield_kgha", "R_season", "R_early", "R_late", "trend", "area_kha"]


OUT = {}  # set in main(): tables, figures, header


def save_table(df: pd.DataFrame, name: str, index: bool = False) -> None:
    path = OUT["tables"] / name
    with open(path, "w") as f:
        f.write(f"# {OUT['header']}\n")
        df.to_csv(f, index=index)
    print(f"  table  -> {U.rel(path)}")


def save_fig(fig, name: str) -> None:
    fig.text(0.01, -0.03, OUT["header"], fontsize=7, color=MUTED, ha="left", va="top")
    path = OUT["figures"] / name
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  figure -> {U.rel(path)}")


def main() -> None:
    a = U.parse_args(__doc__.splitlines()[0])
    OUT.update(tables=a.outdir / "tables", figures=a.outdir / "figures", header=U.header(a.panel))
    OUT["tables"].mkdir(parents=True, exist_ok=True)
    OUT["figures"].mkdir(parents=True, exist_ok=True)
    p = pd.read_csv(a.panel)
    assert set(p.subdivision) <= set(SUB_ORDER), "unexpected subdivision in panel"
    print(OUT["header"])
    print(f"Panel: {len(p)} rows, {p.district.nunique()} districts, {p.year.min()}-{p.year.max()}")

    # 1. Summary statistics.
    summ = p[VARS].describe().T
    summ["cv"] = summ["std"] / summ["mean"]
    save_table(summ.reset_index(names="variable"), "eda_summary_stats.csv")
    print(summ.to_string(float_format="%.2f"))

    # 2. Mean yield by year.
    by_year = p.groupby("year").agg(mean_yield_kgha=("yield_kgha", "mean"),
                                    sd_yield_kgha=("yield_kgha", "std"),
                                    mean_ln_yield=("ln_yield", "mean"),
                                    n_districts=("district", "nunique")).reset_index()
    save_table(by_year, "eda_mean_yield_by_year.csv")
    by_year_sub = p.groupby(["year", "subdivision"]).yield_kgha.mean().unstack()
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(by_year.year, by_year.mean_yield_kgha, color=INK, lw=2.5, label="All 13 districts")
    for s in SUB_ORDER:
        ax.plot(by_year_sub.index, by_year_sub[s], color=SUB_COLOR[s], marker=SUB_MARKER[s], ms=5, lw=1.5,
                label=SUB_LABEL[s])
    ax.set(title="Mean soybean yield by year", xlabel="Year", ylabel="Yield (kg/ha)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, ncol=2, loc="lower left")
    save_fig(fig, "eda_mean_yield_by_year.png")

    # 3. District-by-year yield heatmap (districts grouped by subdivision).
    order = p.assign(o=p.subdivision.map({s: i for i, s in enumerate(SUB_ORDER)})) \
             .sort_values(["o", "district"]).district.unique()
    hm = p.pivot(index="district", columns="year", values="yield_kgha").loc[order]
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(hm, cmap=SEQ, ax=ax, linewidths=1, linecolor=SURFACE,
                cbar_kws={"label": "Yield (kg/ha)"}, annot=False)
    ax.set(title="Soybean yield by district and year", xlabel="Year", ylabel="")
    ax.set_yticklabels([f"{d}  ({SUB_LABEL[p.loc[p.district == d, 'subdivision'].iat[0]]})" for d in order],
                       rotation=0)
    ax.grid(False)
    save_fig(fig, "eda_yield_heatmap.png")

    # 4. Yield vs R_season coloured by subdivision.
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for s in SUB_ORDER:
        q = p[p.subdivision == s]
        ax.scatter(q.R_season, q.yield_kgha, s=36, color=SUB_COLOR[s], marker=SUB_MARKER[s],
                   edgecolor=SURFACE, linewidth=1, label=f"{SUB_LABEL[s]} ({q.district.nunique()} districts)")
    ax.set(title="Yield vs Jun-Sep rainfall (district-years)", xlabel="R_season, Jun-Sep rainfall (mm)",
           ylabel="Yield (kg/ha)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.text(1.02, 0.0, "Districts in a subdivision share one\nrainfall value per year, so points\nstack in vertical columns.",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=7.5, color=INK2)
    save_fig(fig, "eda_yield_vs_rseason.png")

    # 5. Rainfall series per subdivision with its mean (small multiples, shared y).
    rain = p.drop_duplicates(["subdivision", "year"])[["subdivision", "year", "R_season", "R_early", "R_late"]]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, s in zip(axes, SUB_ORDER):
        q = rain[rain.subdivision == s]
        mu = q.R_season.mean()
        ax.plot(q.year, q.R_season, color=SUB_COLOR[s], marker=SUB_MARKER[s], ms=5)
        ax.axhline(mu, color=INK2, lw=1, ls="--")
        ax.text(q.year.max() + 0.4, mu, f"mean\n{mu:.0f} mm", va="center", ha="left", fontsize=8, color=INK2)
        ax.set(title=SUB_LABEL[s], xlabel="Year")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    axes[0].set_ylabel("R_season, Jun-Sep rainfall (mm)")
    axes[0].set_ylim(bottom=0)
    fig.suptitle("Jun-Sep rainfall by IMD subdivision, with period mean", fontweight="bold", y=1.02)
    save_fig(fig, "eda_rainfall_by_subdivision.png")

    # 6. Correlation matrix (pooled over district-years).
    corr = p[VARS].corr()
    save_table(corr.reset_index(names="variable"), "eda_correlation.csv")
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    sns.heatmap(corr, cmap=DIV, vmin=-1, vmax=1, annot=True, fmt=".2f", ax=ax, square=True,
                linewidths=1, linecolor=SURFACE, annot_kws={"color": INK, "fontsize": 8},
                cbar_kws={"label": "Pearson r"})
    ax.set_title("Correlation matrix (pooled district-years)")
    ax.grid(False)
    save_fig(fig, "eda_correlation_matrix.png")
    print("\nCorrelation matrix:")
    print(corr.to_string(float_format="%.2f"))

    # 7. Outliers: district-years more than OUTLIER_SD SDs from the district mean.
    g = p.groupby("district")
    p["z_yield"] = (p.yield_kgha - g.yield_kgha.transform("mean")) / g.yield_kgha.transform("std")
    p["z_ln_yield"] = (p.ln_yield - g.ln_yield.transform("mean")) / g.ln_yield.transform("std")
    out = p[(p.z_yield.abs() > C.OUTLIER_SD) | (p.z_ln_yield.abs() > C.OUTLIER_SD)][
        ["district", "subdivision", "year", "area_kha", "yield_kgha", "z_yield", "ln_yield", "z_ln_yield",
         "R_season"]].sort_values("z_ln_yield")
    save_table(out, "eda_outliers.csv")
    print(f"\nOutliers (|z| > {C.OUTLIER_SD:g} on yield or ln yield, within district): {len(out)}")
    print(out.to_string(index=False, float_format="%.2f") if len(out) else "  none")
    print(f"Largest |z| on yield: {p.z_yield.abs().max():.2f}; on ln yield: {p.z_ln_yield.abs().max():.2f}")
    near = p[(p.z_yield.abs() > 2.5) | (p.z_ln_yield.abs() > 2.5)][["district", "year", "yield_kgha", "z_yield", "z_ln_yield"]]
    print("District-years with |z| > 2.5 (for context):")
    print(near.to_string(index=False, float_format="%.2f") if len(near) else "  none")

    # 8. Rainfall context per subdivision, for the 100 mm shock.
    rows = []
    for s in SUB_ORDER:
        q = rain[rain.subdivision == s]
        for v in ["R_season", "R_early", "R_late"]:
            mu, sd = q[v].mean(), q[v].std()
            rows.append({"subdivision": s, "variable": v, "n_years": len(q), "mean_mm": mu, "sd_mm": sd,
                         "min_mm": q[v].min(), "max_mm": q[v].max(),
                         "shock_mm": C.RAIN_SHOCK_MM, "shock_in_sd": C.RAIN_SHOCK_MM / sd,
                         "shock_pct_of_mean": 100 * C.RAIN_SHOCK_MM / mu})
    ctx = pd.DataFrame(rows)
    save_table(ctx, "eda_subdivision_rainfall_context.csv")
    print(f"\nRainfall per subdivision ({p.year.min()}-{p.year.max()}) and the {C.RAIN_SHOCK_MM:g} mm shock:")
    print(ctx.to_string(index=False, float_format="%.2f"))


if __name__ == "__main__":
    main()
