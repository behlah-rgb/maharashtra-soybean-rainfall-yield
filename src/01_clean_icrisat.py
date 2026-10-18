"""Step 1: clean ICRISAT soybean data and apply the district selection rule.

Reads  : config.ICRISAT_FILE
Writes : config.DISTRICT_MAP_FILE, config.SOY_CLEAN_FILE, config.ICRISAT_AUDIT_FILE,
         outputs/tables/icrisat_yield_check.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

# Rename by header name, never by position.
RENAME = {
    "Dist Code": "dist_code",
    "Year": "year",
    "State Name": "state",
    "Dist Name": "district",
    f"{C.CROP} AREA (1000 ha)": "area_kha",
    f"{C.CROP} PRODUCTION (1000 tons)": "prod_kt",
    f"{C.CROP} YIELD (Kg per ha)": "yield_kgha",
}


def write_district_map() -> pd.DataFrame:
    rows = [(d, s) for s, ds in C.DISTRICT_SUBDIVISION.items() for d in ds]
    m = pd.DataFrame(rows, columns=["district", "subdivision"])
    assert not m.district.duplicated().any(), "district appears twice in the map"
    C.DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    m.to_csv(C.DISTRICT_MAP_FILE, index=False)
    return m


def main() -> None:
    raw = pd.read_csv(C.ICRISAT_FILE)
    missing_cols = set(RENAME) - set(raw.columns)
    assert not missing_cols, f"expected ICRISAT columns not found: {missing_cols}"
    print(f"ICRISAT raw: {raw.shape[0]} rows, {raw.shape[1]} columns")
    print("Unit check from headers:", [c for c in RENAME if "(" in c])

    d = raw[list(RENAME)].rename(columns=RENAME)
    assert (d.state == C.STATE_NAME).all(), "rows from another state"
    assert d.isna().sum().sum() == 0, "missing values in ICRISAT soybean columns"
    assert not d.duplicated(["district", "year"]).any(), "duplicate district-year rows"
    d = d[d.year.between(C.YEAR_START, C.YEAR_END_TARGET)].copy()

    # Every ICRISAT district must be in the map.
    m = write_district_map()
    unmapped = sorted(set(d.district) - set(m.district))
    assert not unmapped, f"ICRISAT districts not in the subdivision map: {unmapped}"
    unused = sorted(set(m.district) - set(d.district))
    print(f"Map: {len(m)} districts, all ICRISAT names mapped. Map names not in ICRISAT: {unused or 'none'}")

    # Zero area = not grown. Check that zero area always comes with zero production and yield.
    assert (d.area_kha >= 0).all() and (d.prod_kt >= 0).all() and (d.yield_kgha >= 0).all()
    zero = d.area_kha == 0
    bad = d[(zero & ((d.prod_kt > 0) | (d.yield_kgha > 0))) | (~zero & (d.yield_kgha == 0))]
    assert bad.empty, f"inconsistent zero area / yield rows:\n{bad}"
    print(f"Zero-area rows (not grown, dropped): {zero.sum()}")

    # Yield consistency: reported yield vs 1000 * production / area (1000 t / 1000 ha -> kg/ha).
    g = d[~zero].copy()
    g["yield_implied"] = 1000.0 * g.prod_kt / g.area_kha
    g["yield_diff"] = g.yield_kgha - g.yield_implied
    g["abs_diff"] = g.yield_diff.abs()
    check = g.sort_values("abs_diff", ascending=False)
    C.OUT_TABLES.mkdir(parents=True, exist_ok=True)
    check[["district", "year", "area_kha", "prod_kt", "yield_kgha", "yield_implied", "yield_diff"]] \
        .to_csv(C.OUT_TABLES / "icrisat_yield_check.csv", index=False)
    print("\nLargest |reported - implied| yield discrepancies (kg/ha):")
    print(check[["district", "year", "area_kha", "prod_kt", "yield_kgha", "yield_implied", "yield_diff"]]
          .head(10).to_string(index=False))
    print(f"max |diff| = {g.abs_diff.max():.4f} kg/ha, mean = {g.abs_diff.mean():.4f}")
    assert g.abs_diff.max() <= C.YIELD_CHECK_TOL, "yield does not match production/area"

    # District rule.
    stats = d.groupby("district").agg(
        dist_code=("dist_code", "first"),
        rows_raw=("year", "size"),
        rows_zero_area=("area_kha", lambda s: int((s == 0).sum())),
        years_grown=("area_kha", lambda s: int((s > 0).sum())),
        years_ge_threshold=("area_kha", lambda s: int((s >= C.AREA_THRESHOLD).sum())),
        mean_area_kha=("area_kha", lambda s: s[s > 0].mean() if (s > 0).any() else np.nan),
        first_year=("year", "min"), last_year=("year", "max"),
    ).reset_index()
    stats["subdivision"] = stats.district.map(m.set_index("district").subdivision)
    stats["selected"] = stats.years_ge_threshold >= C.MIN_YEARS
    selected = sorted(stats.loc[stats.selected, "district"])

    # Rows kept / dropped and why.
    stats["rows_kept"] = np.where(stats.selected, stats.years_grown, 0)
    stats["rows_dropped"] = stats.rows_raw - stats.rows_kept
    def reason(r):
        parts = []
        if not r.selected:
            parts.append(f"district fails rule ({r.years_ge_threshold} yrs with area>={C.AREA_THRESHOLD:g}k ha "
                         f"< {C.MIN_YEARS}): all {r.rows_raw} rows")
        elif r.rows_zero_area:
            parts.append(f"{r.rows_zero_area} zero-area rows (not grown)")
        if r.rows_raw < C.YEAR_END_TARGET - C.YEAR_START + 1:
            parts.append(f"only {r.rows_raw} years in raw file")
        return "; ".join(parts) or "none"
    stats["drop_reason"] = stats.apply(reason, axis=1)
    stats = stats.sort_values(["selected", "mean_area_kha"], ascending=[False, False])
    stats.to_csv(C.ICRISAT_AUDIT_FILE, index=False)
    print("\nAudit (saved to", C.ICRISAT_AUDIT_FILE.relative_to(C.ROOT), "):")
    print(stats[["district", "subdivision", "years_grown", "years_ge_threshold", "mean_area_kha",
                 "selected", "rows_dropped", "drop_reason"]].to_string(index=False, float_format="%.1f"))

    # Compare with the expected list.
    exp = set(C.EXPECTED_DISTRICTS)
    print(f"\nSelected ({len(selected)}): {selected}")
    print(f"In expected list but not selected: {sorted(exp - set(selected)) or 'none'}")
    print(f"Selected but not in expected list: {sorted(set(selected) - exp) or 'none'}")

    # Sensitivity: the same rule counted over the fallback window only (reported, not used).
    fb = d[d.year <= C.YEAR_END_FALLBACK]
    n_fb = fb[fb.area_kha >= C.AREA_THRESHOLD].groupby("district").size()
    sel_fb = sorted(n_fb[n_fb >= C.MIN_YEARS].index)
    print(f"Sensitivity - rule counted over {C.YEAR_START}-{C.YEAR_END_FALLBACK} only would give "
          f"{len(sel_fb)}: lose {sorted(set(selected) - set(sel_fb)) or 'none'}, "
          f"gain {sorted(set(sel_fb) - set(selected)) or 'none'}")

    clean = g[g.district.isin(selected)][
        ["dist_code", "district", "year", "area_kha", "prod_kt", "yield_kgha", "yield_implied"]
    ].sort_values(["district", "year"]).reset_index(drop=True)
    clean["subdivision"] = clean.district.map(m.set_index("district").subdivision)
    assert clean.isna().sum().sum() == 0
    C.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    clean.to_csv(C.SOY_CLEAN_FILE, index=False)
    print(f"\nSaved {C.SOY_CLEAN_FILE.relative_to(C.ROOT)}: {len(clean)} rows, "
          f"{clean.district.nunique()} districts, years {clean.year.min()}-{clean.year.max()}")
    per = clean.groupby("district").year.agg(["size", "min", "max"])
    print("Rows per selected district:", per["size"].to_dict())
    print("Selected districts by subdivision:", clean.groupby("subdivision").district.nunique().to_dict())


if __name__ == "__main__":
    main()
