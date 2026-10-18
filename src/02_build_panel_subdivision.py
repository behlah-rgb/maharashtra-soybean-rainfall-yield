"""Step 2: build the fallback panel with IMD subdivision rainfall (PROTOTYPE).

Reads  : config.SOY_CLEAN_FILE, config.IMD_SUBDIV_FILE, config.DISTRICT_MAP_FILE
Writes : config.PANEL_V1_FILE, config.PANEL_V1_WIDE_FILE (robustness district set),
         data/interim/subdivision_rainfall.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

PANEL_COLS = ["district", "dist_code", "subdivision", "year", "trend",
              "area_kha", "prod_kt", "yield_kgha", "ln_yield",
              "R_season", "R_early", "R_late", "R_julsep"]


def subdivision_rainfall() -> pd.DataFrame:
    r = pd.read_csv(C.IMD_SUBDIV_FILE)
    need = {"SUBDIVISION", "YEAR", "Jun-Sep", *C.MONTHS_SEASON}
    assert need <= set(r.columns), f"IMD columns missing: {need - set(r.columns)}"
    subs = list(C.DISTRICT_SUBDIVISION)
    absent = set(subs) - set(r.SUBDIVISION)
    assert not absent, f"subdivisions not in IMD file: {absent}"
    r = r[r.SUBDIVISION.isin(subs) & r.YEAR.between(C.YEAR_START, C.YEAR_END_FALLBACK)].copy()
    assert not r.duplicated(["SUBDIVISION", "YEAR"]).any()
    assert len(r) == len(subs) * (C.YEAR_END_FALLBACK - C.YEAR_START + 1), "IMD subdivision-years missing"
    assert r[C.MONTHS_SEASON].isna().sum().sum() == 0, "missing monthly rainfall"

    r["R_season"] = r[C.MONTHS_SEASON].sum(axis=1)
    r["R_early"] = r[C.MONTHS_EARLY].sum(axis=1)
    r["R_late"] = r[C.MONTHS_LATE].sum(axis=1)
    r["R_julsep"] = r[C.MONTHS_JULSEP].sum(axis=1)  # alternative window for robustness (src/09)
    # Cross-check our Jun-Sep sum against the file's own Jun-Sep column.
    dev = (r.R_season - r["Jun-Sep"]).abs()
    print(f"Check: computed Jun-Sep vs IMD 'Jun-Sep' column, max |diff| = {dev.max():.2f} mm")
    if dev.max() > 0.5:
        print(r.loc[dev > 0.5, ["SUBDIVISION", "YEAR", "Jun-Sep", "R_season"]])
    assert dev.max() <= 1.0, "monthly sums disagree with the file's seasonal total"
    out = r.rename(columns={"SUBDIVISION": "subdivision", "YEAR": "year"})[
        ["subdivision", "year", "R_season", "R_early", "R_late", "R_julsep"]]
    out.to_csv(C.DATA_INTERIM / "subdivision_rainfall.csv", index=False)
    return out


def build(soy_path: Path, out_path: Path, rain: pd.DataFrame) -> pd.DataFrame:
    soy = pd.read_csv(soy_path)
    m = pd.read_csv(C.DISTRICT_MAP_FILE)
    unmapped = sorted(set(soy.district) - set(m.district))
    assert not unmapped, f"districts not in map: {unmapped}"
    # Subdivision comes from the map file (not carried over from step 1), then checked for agreement.
    soy = soy.drop(columns="subdivision").merge(m, on="district", how="left", validate="many_to_one")

    soy = soy[soy.year.between(C.YEAR_START, C.YEAR_END_FALLBACK)]
    p = soy.merge(rain, on=["subdivision", "year"], how="left", validate="many_to_one")

    p["ln_yield"] = np.log(p.yield_kgha)
    p["trend"] = p.year - C.TREND_BASE_YEAR
    p = p[PANEL_COLS].sort_values(["district", "year"]).reset_index(drop=True)

    n_d, n_t = p.district.nunique(), C.YEAR_END_FALLBACK - C.YEAR_START + 1
    assert len(p) == n_d * n_t, f"rows {len(p)} != districts {n_d} x years {n_t}"
    assert not p.duplicated(["district", "year"]).any()
    na = p.isna().sum()
    assert na.sum() == 0, f"unexpected missing values:\n{na[na > 0]}"
    assert np.isfinite(p.ln_yield).all()

    p.to_csv(out_path, index=False)
    print(f"Saved {out_path.relative_to(C.ROOT)}: {len(p)} rows = {n_d} districts x {n_t} years "
          f"({p.year.min()}-{p.year.max()}), no missing values")
    print("Districts per subdivision:", p.groupby("subdivision").district.nunique().to_dict())
    print(f"Independent rainfall series in panel: {p.subdivision.nunique()} ({sorted(p.subdivision.unique())})")
    print("\nColumn summary:")
    print(p.describe().T[["count", "mean", "std", "min", "max"]].to_string(float_format="%.3f"))
    return p


def main() -> None:
    print(C.PROTOTYPE_HEADER)
    rain = subdivision_rainfall()
    p = build(C.SOY_CLEAN_FILE, C.PANEL_V1_FILE, rain)
    print("\n--- Robustness panel: wider district set (SPEC amendment A5) ---")
    w = build(C.SOY_CLEAN_WIDE_FILE, C.PANEL_V1_WIDE_FILE, rain)
    assert set(p.district) < set(w.district)
    assert sorted(set(w.district) - set(p.district)) == sorted(C.ROBUST_EXTRA_DISTRICTS)


if __name__ == "__main__":
    main()
