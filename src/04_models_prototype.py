"""Step 4: prototype fixed-effects models on the subdivision panel (PROTOTYPE - NOT FOR THE REPORT).

Models (district FE + linear trend, SEs clustered by year):
  linear          ln Y = a_d + g t + b1 R_season
  quadratic       ln Y = a_d + g t + b1 R_season + b2 R_season^2
  timing_linear   ln Y = a_d + g t + b1 R_early + b3 R_late
  timing_quad     ln Y = a_d + g t + b1 R_early + b2 R_early^2 + b3 R_late + b4 R_late^2

100 mm experiment: pct = exp(f(Rbar - 100) - f(Rbar)) - 1 at each subdivision's mean rainfall,
with a bootstrap interval from resampling whole years.

Reads  : config.PANEL_V1_FILE
Writes : config.PROTOTYPE_LOG_FILE, outputs/tables/prototype_coefficients.csv,
         outputs/tables/prototype_100mm_experiment.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

OUTCOME = "ln_yield"
# Each model: rainfall terms as {window variable: include square?}
MODELS = {
    "linear": {"R_season": False},
    "quadratic": {"R_season": True},
    "timing_linear": {"R_early": False, "R_late": False},
    "timing_quad": {"R_early": True, "R_late": True},
}


class Tee:
    """Write to stdout and the log file at the same time."""
    def __init__(self, path):
        self.f = open(path, "w")
    def __call__(self, *args):
        s = " ".join(str(a) for a in args)
        print(s)
        self.f.write(s + "\n")
    def close(self):
        self.f.close()


def regressors(spec: dict) -> list:
    cols = ["trend"]
    for v, sq in spec.items():
        cols.append(v)
        if sq:
            cols.append(f"{v}_sq")
    return cols


def fit(df: pd.DataFrame, spec: dict, time_col: str = "year"):
    d = df.set_index(["district", time_col])
    exog = d[regressors(spec)]
    return PanelOLS(d[OUTCOME], exog, entity_effects=True).fit(cov_type="clustered", cluster_time=True)


def rain_part(params: pd.Series, var: str, r: float) -> float:
    """Fitted rainfall contribution f(r) of one window."""
    out = params[var] * r
    if f"{var}_sq" in params.index:
        out += params[f"{var}_sq"] * r ** 2
    return out


def pct_change(params: pd.Series, var: str, rbar: float) -> float:
    delta = rain_part(params, var, rbar - C.RAIN_SHOCK_MM) - rain_part(params, var, rbar)
    return float(np.exp(delta) - 1.0)


def experiments(params: pd.Series, spec: dict, means: pd.DataFrame) -> list:
    """One row per (subdivision, shocked window)."""
    rows = []
    for sub, m in means.iterrows():
        for var in spec:
            rows.append({"subdivision": sub, "shocked_window": var, "Rbar_mm": m[var],
                         "pct_change": pct_change(params, var, m[var])})
    return rows


def main() -> None:
    C.OUT_LOGS.mkdir(parents=True, exist_ok=True)
    log = Tee(C.PROTOTYPE_LOG_FILE)
    warnings.simplefilter("ignore", category=FutureWarning)
    log("=" * 88)
    log(C.PROTOTYPE_HEADER)
    log("=" * 88)

    p = pd.read_csv(C.PANEL_V1_FILE)
    for v in ["R_season", "R_early", "R_late"]:
        p[f"{v}_sq"] = p[v] ** 2
    n_d, n_t = p.district.nunique(), p.year.nunique()
    assert len(p) == n_d * n_t and p.isna().sum().sum() == 0
    log(f"Panel: {len(p)} obs = {n_d} districts x {n_t} years ({p.year.min()}-{p.year.max()}); "
        f"outcome {OUTCOME}; rainfall in mm")
    log(f"Independent rainfall series: {p.subdivision.nunique()} subdivisions; "
        f"year clusters: {n_t}. Cluster-robust SEs with {n_t} clusters are unreliable; treat as indicative.")
    log("Estimator: linearmodels PanelOLS, entity (district) effects + linear trend (year - "
        f"{C.TREND_BASE_YEAR}), SEs clustered by year.\n")

    # Subdivision mean rainfall (Rbar). Every district in a subdivision has the same series and the
    # panel is balanced, so the district mean equals the subdivision mean.
    means = p.groupby("subdivision")[["R_season", "R_early", "R_late"]].mean()
    dmeans = p.groupby("district")[["R_season", "R_early", "R_late"]].mean()
    dsub = p.drop_duplicates("district").set_index("district").subdivision
    assert np.allclose(dmeans.values, means.loc[dsub[dmeans.index]].values), "district mean != subdivision mean"
    log("Mean rainfall per subdivision used as Rbar (mm):")
    log(means.round(1).to_string() + "\n")

    coef_rows, exp_rows, point = [], [], {}
    for name, spec in MODELS.items():
        res = fit(p, spec)
        point[name] = res.params
        log("-" * 88)
        log(f"MODEL: {name}   regressors: {', '.join(regressors(spec))}")
        log("-" * 88)
        tab = pd.DataFrame({"coef": res.params, "se_cluster_year": res.std_errors,
                            "t": res.tstats, "p": res.pvalues})
        log(tab.to_string(float_format=lambda x: f"{x:.6g}"))
        log(f"within R-squared = {res.rsquared_within:.4f}   N = {res.nobs}   entities = {res.entity_info['total']:.0f}")
        sq = [c for c in res.params.index if c.endswith("_sq")]
        if sq:
            w = res.wald_test(formula=[f"{c} = 0" for c in sq])
            q = len(sq)
            log(f"Joint test of squared terms ({', '.join(sq)} = 0), clustered covariance: "
                f"Wald chi2({q}) = {w.stat:.4f}, p = {w.pval:.4f}; F = Wald/q = {w.stat / q:.4f}")
            for v in spec:
                if spec[v]:
                    b1, b2 = res.params[v], res.params[f"{v}_sq"]
                    tp = -b1 / (2 * b2)
                    lo, hi = p[v].min(), p[v].max()
                    log(f"  {v}: turning point -b1/(2 b2) = {tp:.1f} mm ({'maximum' if b2 < 0 else 'minimum'}); "
                        f"observed range {lo:.1f}-{hi:.1f} mm")
        if name == "linear":
            log(f"Linear check: exp(-{C.RAIN_SHOCK_MM:g} * b1) - 1 = "
                f"{np.exp(-C.RAIN_SHOCK_MM * res.params['R_season']) - 1:.6f}")
        for c in res.params.index:
            coef_rows.append({"model": name, "term": c, "coef": res.params[c], "se_cluster_year": res.std_errors[c],
                              "p": res.pvalues[c], "within_r2": res.rsquared_within})
        for r in experiments(res.params, spec, means):
            exp_rows.append({"model": name, **r})
        log("")

    # Bootstrap: resample whole years with replacement; relabel draws so the panel index stays unique,
    # keep each draw's original trend value.
    rng = np.random.default_rng(C.SEED)
    years = np.sort(p.year.unique())
    by_year = {y: g for y, g in p.groupby("year")}
    boot_pct = {i: [] for i in range(len(exp_rows))}
    boot_coef = {name: [] for name in MODELS}
    n_fail = {name: 0 for name in MODELS}
    for b in range(C.N_BOOT):
        draw = rng.choice(years, size=len(years), replace=True)
        bd = pd.concat([by_year[y].assign(draw=k) for k, y in enumerate(draw)], ignore_index=True)
        i = 0
        for name, spec in MODELS.items():
            n_rows = len(spec) * len(means)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    prm = fit(bd, spec, time_col="draw").params
                assert np.all(np.isfinite(prm))
                boot_coef[name].append(prm)
                vals = [r["pct_change"] for r in experiments(prm, spec, means)]
            except Exception:
                n_fail[name] += 1
                vals = [np.nan] * n_rows
            for j, v in enumerate(vals):
                boot_pct[i + j].append(v)
            i += n_rows

    exp_df = pd.DataFrame(exp_rows)
    arr = [np.array(boot_pct[i]) for i in range(len(exp_rows))]
    exp_df["boot_lo_2.5"] = [np.nanpercentile(a, 2.5) for a in arr]
    exp_df["boot_hi_97.5"] = [np.nanpercentile(a, 97.5) for a in arr]
    exp_df["boot_median"] = [np.nanmedian(a) for a in arr]
    exp_df["boot_valid_reps"] = [int(np.isfinite(a).sum()) for a in arr]

    coef_df = pd.DataFrame(coef_rows)
    coef_df["se_boot_years"] = [pd.DataFrame(boot_coef[r.model])[r.term].std() for r in coef_df.itertuples()]

    log("=" * 88)
    log(f"BOOTSTRAP: {C.N_BOOT} reps, resampling {len(years)} years with replacement, seed {C.SEED}. "
        f"Failed fits per model: {n_fail}")
    log("=" * 88)
    log("Coefficient SEs: clustered by year vs bootstrap over years")
    log(coef_df[["model", "term", "coef", "se_cluster_year", "se_boot_years", "p", "within_r2"]]
        .to_string(index=False, float_format=lambda x: f"{x:.6g}"))
    log("")
    log(f"{C.RAIN_SHOCK_MM:g} mm DEFICIT EXPERIMENT: percent change in yield = exp(f(Rbar-{C.RAIN_SHOCK_MM:g}) - f(Rbar)) - 1,")
    log("at each subdivision's mean rainfall. For timing models the deficit is applied to one window at a time.")
    log("Shown in percent (the CSV stores proportions: -0.05 = -5%). 95% percentile bootstrap interval over years.")
    show = exp_df.copy()
    for c in ["pct_change", "boot_lo_2.5", "boot_hi_97.5", "boot_median"]:
        show[c] = (100 * show[c]).map(lambda x: f"{x:+.2f}%")
    show["Rbar_mm"] = show.Rbar_mm.map(lambda x: f"{x:.1f}")
    log(show.to_string(index=False))
    log("")
    log("Caveats: rainfall is subdivision-level (3 independent series), so effective rainfall variation is far")
    log("smaller than N suggests; 16 year-clusters are too few for reliable cluster-robust inference; no")
    log("temperature control. Results are associations under the model's assumptions, not causal effects.")
    log(C.PROTOTYPE_HEADER)
    log.close()

    for df, name in [(coef_df, "prototype_coefficients.csv"), (exp_df, "prototype_100mm_experiment.csv")]:
        with open(C.OUT_TABLES / name, "w") as f:
            f.write(f"# {C.PROTOTYPE_HEADER}\n")
            df.to_csv(f, index=False)
    print(f"\nWrote {C.PROTOTYPE_LOG_FILE.relative_to(C.ROOT)} and outputs/tables/prototype_*.csv")


if __name__ == "__main__":
    main()
