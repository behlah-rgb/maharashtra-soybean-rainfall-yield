"""Shared helpers for src/06-09 (not a numbered step; imported by those scripts).

- CLI parsing (panel path + output folder) and the outputs/final guard.
- Output header: PROTOTYPE unless the input is config.PANEL_FINAL_FILE.
- Panel loading and checks.
- Fixed-effects fitting (linearmodels PanelOLS) and a fast within estimator for bootstraps.
- Rainfall response f(R) and scenario effects.
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

RAIN_VARS = ["R_season", "R_early", "R_late", "R_julsep"]

# Model catalogue. rain: {window: include square?}
MODELS = {
    "linear": {"outcome": "ln_yield", "rain": {"R_season": False}, "role": "headline"},
    "quadratic": {"outcome": "ln_yield", "rain": {"R_season": True}, "role": "headline"},
    "linear_level": {"outcome": "yield_kgha", "rain": {"R_season": False}, "role": "robustness outcome (kg/ha)"},
    "quadratic_level": {"outcome": "yield_kgha", "rain": {"R_season": True}, "role": "robustness outcome (kg/ha)"},
    "timing_linear": {"outcome": "ln_yield", "rain": {"R_early": False, "R_late": False}, "role": "secondary"},
    "timing_quad": {"outcome": "ln_yield", "rain": {"R_early": True, "R_late": True}, "role": "exploratory"},
}


# ---- CLI and guard -------------------------------------------------------------------------
def parse_args(description: str, wide: bool = False) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("panel", type=Path, help="panel CSV (panel_v1.csv or panel_final.csv)")
    ap.add_argument("outdir", type=Path, help="output folder (e.g. outputs/prototype or outputs/final)")
    if wide:
        ap.add_argument("--wide-panel", type=Path, default=None,
                        help="panel for the wider district set (panel_v1_wide.csv or panel_final_wide.csv)")
    a = ap.parse_args()
    a.panel = a.panel.resolve()
    a.outdir = a.outdir.resolve()
    if wide and a.wide_panel is not None:
        a.wide_panel = a.wide_panel.resolve()
    check_output_target(a.panel, a.outdir, getattr(a, "wide_panel", None))
    return a


def _inside(path: Path, root: Path) -> bool:
    root = root.resolve()
    return path == root or root in path.parents


def is_final(panel: Path) -> bool:
    return panel.resolve() == C.PANEL_FINAL_FILE.resolve()


def check_output_target(panel: Path, outdir: Path, wide_panel: Path | None = None) -> None:
    """Refuse to write under outputs/final unless the input is panel_final.csv (and, for the wider
    district set, panel_final_wide.csv). Exits with an error message; never falls back silently."""
    if not panel.exists():
        sys.exit(f"ERROR: panel file not found: {panel}")
    if _inside(outdir, C.OUT_FINAL):
        if not is_final(panel):
            sys.exit(f"REFUSED: output folder {outdir} is under outputs/final, but the input is {panel.name}. "
                     f"Only {C.PANEL_FINAL_FILE.relative_to(C.ROOT)} may write to outputs/final.")
        if wide_panel is not None and wide_panel.resolve() != C.PANEL_FINAL_WIDE_FILE.resolve():
            sys.exit(f"REFUSED: final run with a non-final wider panel ({wide_panel.name}).")
    if is_final(panel) and wide_panel is not None and wide_panel.resolve() != C.PANEL_FINAL_WIDE_FILE.resolve():
        sys.exit("REFUSED: mixing panel_final.csv with a non-final wider panel.")


def header(panel: Path) -> str:
    return C.FINAL_HEADER if is_final(panel) else C.PROTOTYPE_HEADER


# ---- Output helpers ------------------------------------------------------------------------
class Outputs:
    """Writes tables (CSV with a '# header' first line), figures (with a footer) and a text log."""

    def __init__(self, outdir: Path, prefix: str, panel: Path):
        self.head = header(panel)
        self.prefix = prefix
        self.tables = outdir / "tables"
        self.figures = outdir / "figures"
        self.logs = outdir / "logs"
        for d in (self.tables, self.figures, self.logs):
            d.mkdir(parents=True, exist_ok=True)
        self._log = open(self.logs / f"{prefix}.txt", "w")
        self.log("=" * 92)
        self.log(self.head)
        self.log("=" * 92)
        self.log(f"Input panel: {rel(panel)}   Output folder: {rel(outdir)}")

    def log(self, *args) -> None:
        s = " ".join(str(a) for a in args)
        print(s)
        self._log.write(s + "\n")

    def table(self, df: pd.DataFrame, name: str, index: bool = False) -> Path:
        path = self.tables / f"{self.prefix}_{name}.csv"
        with open(path, "w") as f:
            f.write(f"# {self.head}\n")
            df.to_csv(f, index=index)
        return path

    def figure(self, fig, name: str) -> Path:
        fig.text(0.01, -0.03, self.head, fontsize=7, color="#898781", ha="left", va="top")
        path = self.figures / f"{self.prefix}_{name}.png"
        fig.savefig(path, bbox_inches="tight", dpi=150)
        import matplotlib.pyplot as plt
        plt.close(fig)
        return path

    def close(self) -> None:
        self.log(self.head)
        self._log.close()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(C.ROOT))
    except ValueError:
        return str(p)


# ---- Panel ---------------------------------------------------------------------------------
def load_panel(path: Path) -> pd.DataFrame:
    p = pd.read_csv(path)
    need = ["district", "subdivision", "year", "trend", "area_kha", "yield_kgha", "ln_yield", *RAIN_VARS]
    miss = set(need) - set(p.columns)
    assert not miss, f"panel lacks columns {miss}"
    assert not p.duplicated(["district", "year"]).any(), "duplicate district-year rows"
    na = p[need].isna().sum()
    assert na.sum() == 0, f"missing values:\n{na[na > 0]}"
    assert (p.yield_kgha > 0).all() and np.allclose(p.ln_yield, np.log(p.yield_kgha))
    for v in RAIN_VARS:
        p[f"{v}_sq"] = p[v] ** 2
    return p.sort_values(["district", "year"]).reset_index(drop=True)


def rainfall_is_district_level(p: pd.DataFrame) -> bool:
    """True if R_season varies across districts within a subdivision-year (gridded data)."""
    n = p.groupby(["subdivision", "year"]).R_season.nunique()
    return bool((n > 1).any())


def describe_panel(p: pd.DataFrame) -> str:
    bal = p.groupby("district").size()
    return (f"{len(p)} obs, {p.district.nunique()} districts, {p.year.nunique()} years "
            f"({p.year.min()}-{p.year.max()}), balanced={bal.nunique() == 1}, "
            f"rainfall district-level={rainfall_is_district_level(p)}, "
            f"distinct R_season series={p.groupby('year').R_season.nunique().max()}")


# ---- Fixed-effects fitting -----------------------------------------------------------------
def rain_terms(rain: dict) -> list:
    out = []
    for v, sq in rain.items():
        out.append(v)
        if sq:
            out.append(f"{v}_sq")
    return out


def design(p: pd.DataFrame, rain: dict, trend: str = "common") -> tuple[pd.DataFrame, bool]:
    """Regressors for the chosen trend specification. Returns (X, time_effects)."""
    X = p[rain_terms(rain)].copy()
    time_effects = False
    if trend == "common":
        X.insert(0, "trend", p.trend)
    elif trend == "district":
        for d in sorted(p.district.unique()):
            X[f"trend_{d}"] = p.trend * (p.district == d)
    elif trend == "year_fe":
        time_effects = True
    elif trend != "none":
        raise ValueError(trend)
    return X, time_effects


COV_METHODS = {  # name -> PanelOLS.fit keyword arguments
    "year_CR": {"cov_type": "clustered", "cluster_time": True},
    "district_CR": {"cov_type": "clustered", "cluster_entity": True},
    "twoway_CR": {"cov_type": "clustered", "cluster_entity": True, "cluster_time": True},
    "driscoll_kraay": {"cov_type": "kernel", "kernel": "bartlett", "bandwidth": C.DK_MAXLAGS},
}


def fit_fe(p: pd.DataFrame, outcome: str, rain: dict, trend: str = "common", weights: str | None = None,
           entity: str = "district", time: str = "year", cov: str = "year_CR"):
    """PanelOLS with entity effects and the chosen trend. Default SEs clustered by year;
    cov selects another method from COV_METHODS."""
    d = p.set_index([entity, time])
    X, te = design(d.reset_index(), rain, trend)
    X.index = d.index
    w = d[weights] if weights else None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = PanelOLS(d[outcome], X, entity_effects=True, time_effects=te, weights=w)
        return mod.fit(**COV_METHODS[cov])


class FastFE:
    """Array version of the within estimator (district effects + common trend + rain terms) for
    bootstraps. fit(rows, codes) refits the full model on the rows `rows` of the panel, with entity
    codes `codes` (so a district drawn twice can be two entities). Same estimates as PanelOLS."""

    def __init__(self, p: pd.DataFrame, outcome: str, rain: dict):
        X, _ = design(p, rain, "common")
        self.cols = list(X.columns)
        self.X = X.to_numpy(float)
        self.y = p[outcome].to_numpy(float)
        self.codes = pd.factorize(p.district)[0]

    def fit(self, rows: np.ndarray, codes: np.ndarray | None = None) -> np.ndarray:
        codes = self.codes[rows] if codes is None else codes
        X, y = self.X[rows], self.y[rows]
        cnt = np.bincount(codes)
        Xm = np.column_stack([np.bincount(codes, X[:, j]) / cnt for j in range(X.shape[1])])
        Z = X - Xm[codes]
        yz = y - (np.bincount(codes, y) / cnt)[codes]
        return np.linalg.lstsq(Z, yz, rcond=None)[0]


def year_rows(p: pd.DataFrame) -> tuple[np.ndarray, list]:
    """Sorted years and, for each, the row positions of that year in p."""
    years = np.sort(p.year.unique())
    return years, [np.flatnonzero(p.year.to_numpy() == y) for y in years]


def block_draws(n_years: int, L: int, B: int, seed: int) -> np.ndarray:
    """Moving-block bootstrap (Kunsch 1989), non-circular: draw ceil(T/L) block starts uniformly from
    0..T-L, concatenate blocks of L consecutive years, truncate to T. Returns (B, T) year positions.
    L = 1 is the iid year bootstrap."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n_years / L))
    starts = rng.integers(0, n_years - L + 1, size=(B, nb))
    pos = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(B, nb * L)
    return pos[:, :n_years]


def rows_from_year_draw(yrows: list, draw: np.ndarray) -> np.ndarray:
    """Rows for one year draw. Districts keep their codes; each drawn year keeps its original trend."""
    return np.concatenate([yrows[k] for k in draw])


def district_draws(n_districts: int, B: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n_districts, size=(B, n_districts))


def rows_from_district_draw(p: pd.DataFrame, draw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows and new entity codes (draw position) for one district draw."""
    codes0 = pd.factorize(p.district)[0]
    drows = [np.flatnonzero(codes0 == d) for d in range(codes0.max() + 1)]
    rows = [drows[d] for d in draw]
    return np.concatenate(rows), np.concatenate([np.full(len(r), k) for k, r in enumerate(rows)])


def wild_cluster_test(p: pd.DataFrame, outcome: str, rain: dict, term: str) -> dict:
    """Wild cluster restricted (WCR) bootstrap-t test of H0: beta_term = 0, clusters = districts,
    Rademacher weights (Cameron, Gelbach and Miller 2008). Works on the district-demeaned data (FWL),
    so the district effects are re-estimated implicitly. Enumerates all 2^G sign vectors when
    G <= WILD_ENUMERATE_MAX_CLUSTERS (exact, no seed); otherwise N_WILD draws with BOOT_SEEDS['wild'].
    The CR small-sample factor cancels between t and t*, so it is omitted."""
    fe = FastFE(p, outcome, rain)
    rows = np.arange(len(p))
    codes = fe.codes
    cnt = np.bincount(codes)
    Z = fe.X - np.column_stack([np.bincount(codes, fe.X[:, j]) / cnt for j in range(fe.X.shape[1])])[codes]
    yz = fe.y - (np.bincount(codes, fe.y) / cnt)[codes]
    j = fe.cols.index(term)
    keep = [i for i in range(Z.shape[1]) if i != j]
    br = np.linalg.lstsq(Z[:, keep], yz, rcond=None)[0]
    yhat_r = Z[:, keep] @ br
    u_r = yz - yhat_r
    A = np.linalg.inv(Z.T @ Z)
    w = Z @ A[j]
    G = cnt.size
    ind = np.zeros((G, len(rows)))
    ind[codes, rows] = 1.0

    def tstat(Y):
        Bh = A @ (Z.T @ Y)
        E = Y - Z @ Bh
        S = ind @ (w[:, None] * E)
        return Bh[j] / np.sqrt((S ** 2).sum(axis=0))

    t0 = float(tstat(yz[:, None])[0])
    if G <= C.WILD_ENUMERATE_MAX_CLUSTERS:
        V = 1.0 - 2.0 * ((np.arange(2 ** G)[None, :] >> np.arange(G)[:, None]) & 1)
        how = f"all 2^{G} = {2 ** G} Rademacher sign vectors (exact)"
    else:
        V = np.random.default_rng(C.BOOT_SEEDS["wild"]).choice([-1.0, 1.0], size=(G, C.N_WILD))
        how = f"{C.N_WILD} random Rademacher draws, seed {C.BOOT_SEEDS['wild']}"
    tb = tstat(yhat_r[:, None] + u_r[:, None] * V[codes, :])
    return {"t": t0, "p": float(np.mean(np.abs(tb) >= abs(t0))), "clusters": G, "draws": how}


def boot_summary(draws: np.ndarray, point: float) -> dict:
    """SE, 95% percentile CI and a two-sided percentile p-value for H0: 0
    (p = 2 x min(share <= 0, share >= 0), capped at 1)."""
    d = draws[np.isfinite(draws)]
    return {"se": float(d.std(ddof=1)), "lo": float(np.percentile(d, 2.5)), "hi": float(np.percentile(d, 97.5)),
            "p": float(min(1.0, 2 * min(np.mean(d <= 0), np.mean(d >= 0)))), "n": int(d.size)}


def fe_params_fast(p: pd.DataFrame, outcome: str, rain: dict, entity: str = "district") -> pd.Series:
    """Within (entity-demeaned) OLS with a common trend; same point estimates as PanelOLS.
    Used in bootstraps for speed. Unweighted, common trend only."""
    X, _ = design(p, rain, "common")
    cols = list(X.columns)
    M = pd.concat([X, p[[outcome]]], axis=1)
    Z = M - M.groupby(p[entity].values).transform("mean")
    beta, *_ = np.linalg.lstsq(Z[cols].to_numpy(float), Z[outcome].to_numpy(float), rcond=None)
    return pd.Series(beta, index=cols)


def lsdv_fit_predict(train: pd.DataFrame, test: pd.DataFrame, outcome: str, rain: dict) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares dummy-variable fit (district dummies + common trend + rain) on train;
    returns (predictions for test, training residuals)."""
    def X(df):
        dums = pd.get_dummies(df.district).reindex(columns=sorted(train.district.unique()), fill_value=False)
        return np.column_stack([dums.to_numpy(float), df.trend.to_numpy(float), df[rain_terms(rain)].to_numpy(float)])
    Xtr = X(train)
    beta, *_ = np.linalg.lstsq(Xtr, train[outcome].to_numpy(float), rcond=None)
    return X(test) @ beta, train[outcome].to_numpy(float) - Xtr @ beta


def gaussian_ic(ssr: float, n: int, k: int) -> dict:
    """AIC/BIC from the Gaussian log-likelihood of the within model.
    llf = -n/2 * (ln(2*pi) + ln(SSR/n) + 1);  AIC = -2 llf + 2k;  BIC = -2 llf + k ln(n);
    k counts slope parameters + entity effects (+ time effects if any)."""
    llf = -0.5 * n * (np.log(2 * np.pi) + np.log(ssr / n) + 1)
    return {"llf": llf, "k": k, "aic": -2 * llf + 2 * k, "bic": -2 * llf + k * np.log(n)}


# ---- Rainfall response and scenarios --------------------------------------------------------
def f_rain(params: pd.Series, var: str, r) -> np.ndarray:
    r = np.asarray(r, float)
    out = params[var] * r
    if f"{var}_sq" in params.index:
        out = out + params[f"{var}_sq"] * r ** 2
    return out


def effect(params: pd.Series, outcome: str, changes: dict, ybar) -> tuple[np.ndarray, np.ndarray]:
    """changes: {var: (r_old, r_new)}. Returns (pct change, kg/ha change).
    ln outcome: pct = exp(sum f(new) - f(old)) - 1, kg/ha = pct * ybar.
    level outcome: kg/ha = sum f(new) - f(old), pct = kg/ha / ybar."""
    delta = sum(f_rain(params, v, new) - f_rain(params, v, old) for v, (old, new) in changes.items())
    ybar = np.asarray(ybar, float)
    if outcome == "ln_yield":
        pct = np.exp(delta) - 1.0
        return pct, pct * ybar
    return delta / ybar, delta


def resample_years(p: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Draw years with replacement; all districts of a drawn year move together. Duplicated years
    get a new time label `draw`; each keeps its original trend value."""
    years = np.sort(p.year.unique())
    by = {y: g for y, g in p.groupby("year")}
    draw = rng.choice(years, size=len(years), replace=True)
    return pd.concat([by[y].assign(draw=k) for k, y in enumerate(draw)], ignore_index=True)


def resample_districts(p: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Draw districts with replacement; duplicated districts get a new entity label `district`
    (original kept in `district_orig`)."""
    ds = np.sort(p.district.unique())
    by = {d: g for d, g in p.groupby("district")}
    draw = rng.choice(ds, size=len(ds), replace=True)
    return pd.concat([by[d].assign(district_orig=d, district=f"{d}#{k}") for k, d in enumerate(draw)],
                     ignore_index=True)


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
        "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e", "xtick.color": "#898781",
        "ytick.color": "#898781", "text.color": "#0b0b0b", "axes.grid": True, "grid.color": "#e1e0d9",
        "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 11, "axes.titleweight": "bold", "font.size": 9, "lines.linewidth": 2,
    })
    return plt


# Palette (same as src/03): subdivision colours + markers; ink colours.
SUB_ORDER = ["VIDARBHA", "MATATHWADA", "MADHYA MAHARASHTRA", "KONKAN & GOA"]
SUB_LABEL = {"VIDARBHA": "Vidarbha", "MATATHWADA": "Marathwada", "MADHYA MAHARASHTRA": "Madhya Maharashtra",
             "KONKAN & GOA": "Konkan & Goa"}
SUB_COLOR = {"VIDARBHA": "#2a78d6", "MATATHWADA": "#eb6834", "MADHYA MAHARASHTRA": "#1baf7a",
             "KONKAN & GOA": "#eda100"}
SUB_MARKER = {"VIDARBHA": "o", "MATATHWADA": "s", "MADHYA MAHARASHTRA": "^", "KONKAN & GOA": "D"}
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
