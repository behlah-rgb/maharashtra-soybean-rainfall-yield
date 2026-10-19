"""Step 5c: diagnose extreme / suspicious gridded rainfall district-years (SPEC A13.4a).

Reads  : config.PANEL_FINAL_FILE, config.OLD_DISTRICT_WEATHER_FILE, config.CELL_WEIGHTS_FILE,
         raw IMD rain files config.IMD_CACHE_DIR/archive/rain/<year>.grd (read as raw bytes with numpy,
         independent of imdlib and of src/05), data/interim/subdivision_rainfall.csv
Writes : outputs/final/tables/05c_*.csv, outputs/final/logs/05c_diagnose_ghats.txt, config.DQ_FLAGS_FILE

Cases: every panel district-year with |R_season - district median| > DQ_ROBUST_Z robust SD
(robust SD = 1.4826 x MAD over the district's years), plus config.DQ_EXTRA_CASES.
Per case, over the rain cells overlapping the old district, 1 Jun-30 Sep: maximum daily cell value,
cell-days and distinct cells over DQ_DAILY_CELL_MM, sentinel/fill values in the raw grid (-999, other
negatives, NaN, > 1000 mm/day), days on which every overlapping cell is exactly 0, the spread of cell
seasonal totals, and gridded vs IMD subdivision totals (years <= 2015).
imdlib check: raw bytes vs imdlib.get_xarray() for each case year (masking of -999, value equality).
Also writes the dq_flag table (rule A13.4c) to data/interim/dq_flags.csv for src/05.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

OUT = C.OUT_FINAL
HEAD = "FINAL panel data-quality diagnosis (src/05c). Descriptive; no model."
NLAT, NLON, LAT0, LON0, STEP = 129, 135, 6.5, 66.5, 0.25


def raw_rain(year: int) -> np.ndarray:
    a = np.fromfile(C.IMD_CACHE_DIR / "archive" / "rain" / f"{year}.grd", dtype="<f4")
    days = a.size // (NLAT * NLON)
    assert days * NLAT * NLON == a.size
    return a.reshape(days, NLAT, NLON)                     # (day, lat, lon), as imdlib.util.read_grd documents


def robust_z(p: pd.DataFrame) -> pd.DataFrame:
    g = p.groupby("district").R_season
    med = g.transform("median")
    mad = g.transform(lambda s: np.median(np.abs(s - s.median())))
    out = p[["district", "subdivision", "year", "R_season"]].copy()
    out["district_median"] = med
    out["robust_sd"] = 1.4826 * mad
    out["robust_z"] = (p.R_season - med) / out.robust_sd
    out["screen_flag"] = out.robust_z.abs() > C.DQ_ROBUST_Z
    return out


def main() -> None:
    import imdlib
    for d in (OUT / "tables", OUT / "logs"):
        d.mkdir(parents=True, exist_ok=True)
    logf = open(OUT / "logs" / "05c_diagnose_ghats.txt", "w")

    def log(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        logf.write(s + "\n")

    def table(df, name):
        path = OUT / "tables" / f"05c_{name}.csv"
        with open(path, "w") as f:
            f.write(f"# {HEAD}\n")
            df.to_csv(f, index=False)
        log(f"table -> {path.relative_to(C.ROOT)}")

    log("=" * 92); log(HEAD); log("=" * 92)
    p = pd.read_csv(C.PANEL_FINAL_FILE)
    wide = pd.read_csv(C.PANEL_FINAL_WIDE_FILE)
    wx = pd.read_csv(C.OLD_DISTRICT_WEATHER_FILE)
    w = pd.read_csv(C.CELL_WEIGHTS_FILE)
    w = w[w.grid.str.startswith("rain")]
    sub = pd.read_csv(C.DATA_INTERIM / "subdivision_rainfall.csv")

    rz = robust_z(p)
    rzw = robust_z(wide)
    log(f"Screen: |robust z| > {C.DQ_ROBUST_Z:g} within district (robust SD = 1.4826 x MAD), 13-district panel:")
    log(rz[rz.screen_flag].to_string(index=False, float_format=lambda x: f"{x:.2f}") if rz.screen_flag.any() else "  none")
    log("Largest |robust z| per district:")
    log(rz.loc[rz.groupby("district").robust_z.apply(lambda s: s.abs().idxmax())]
        .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    extra_w = rzw[rzw.screen_flag & ~rzw.district.isin(p.district.unique())]
    log(f"Wide-panel extra districts screened: {extra_w[['district', 'year']].values.tolist() or 'none'}")
    table(rz, "robust_z_panel")

    cases = [(r.district, int(r.year), "screen |robust z| > 3") for r in rz[rz.screen_flag].itertuples()]
    cases += [(d, y, "named by team lead") for d, y in C.DQ_EXTRA_CASES]
    sub_of = wx.drop_duplicates("district").set_index("district").subdivision
    area_w = wx.assign(a=wx.district.map(w.groupby("district").overlap_km2.sum()))

    rows, mask_rows = [], []
    cache = {}
    for dist, year, why in cases:
        if year not in cache:
            cache[year] = raw_rain(year)
        A = cache[year]
        t = pd.date_range(f"{year}-01-01", periods=A.shape[0])
        s = (t >= f"{year}-06-01") & (t <= f"{year}-09-30")
        wd = w[w.district == dist]
        X = A[s][:, wd.ilat.to_numpy(), wd.ilon.to_numpy()]            # season days x cells (raw)
        sentinel = X == -999.0
        other_neg = (X < 0) & ~sentinel
        valid = np.where(sentinel, np.nan, X)
        imax = np.unravel_index(np.nanargmax(valid), valid.shape)
        over = valid > C.DQ_DAILY_CELL_MM
        cell_tot = np.nansum(valid, axis=0)
        allzero_days = int((np.nan_to_num(valid) == 0).all(axis=1).sum())
        # typical all-zero days for this district in other years
        typ = []
        for yy in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1):
            if yy == year:
                continue
            if yy not in cache:
                cache[yy] = raw_rain(yy)
            B = cache[yy]
            tt = pd.date_range(f"{yy}-01-01", periods=B.shape[0])
            ss = (tt >= f"{yy}-06-01") & (tt <= f"{yy}-09-30")
            Y = B[ss][:, wd.ilat.to_numpy(), wd.ilon.to_numpy()]
            typ.append(int((np.where(Y == -999, 0, Y) == 0).all(axis=1).sum()))
        sd = sub_of[dist]
        imd = sub[(sub.subdivision == sd) & (sub.year == year)].R_season
        gsub = area_w[(area_w.subdivision == sd) & (area_w.year == year)]
        g_sub_total = np.average(gsub.R_season, weights=gsub.a)
        gr = float(wx[(wx.district == dist) & (wx.year == year)].R_season.iat[0])
        rows.append({
            "district": dist, "year": year, "why": why, "subdivision": sd, "gridded_R_season_mm": gr,
            "district_median_mm": float(wx[wx.district == dist].R_season.median()),
            "n_cells": len(wd), "max_daily_cell_mm": float(valid[imax]),
            "max_cell_date": str(t[s][imax[0]].date()),
            "max_cell_lon_lat": f"{wd.lon.iat[imax[1]]:.3f},{wd.lat.iat[imax[1]]:.3f}",
            "cell_days_gt_300": int(over.sum()), "cells_with_day_gt_300": int(over.any(axis=0).sum()),
            "sentinel_minus999": int(sentinel.sum()), "other_negative": int(other_neg.sum()),
            "nan_in_raw": int(np.isnan(X).sum()), "values_gt_1000": int((valid > 1000).sum()),
            "days_all_cells_zero": allzero_days, "median_days_all_zero_other_years": float(np.median(typ)),
            "cell_season_total_min_mm": float(cell_tot.min()), "cell_season_total_max_mm": float(cell_tot.max()),
            "gridded_subdivision_total_mm": float(g_sub_total),
            "imd_subdivision_total_mm": float(imd.iat[0]) if len(imd) else np.nan,
            "ratio_gridded_sub_over_imd": float(g_sub_total / imd.iat[0]) if len(imd) else np.nan,
        })
        # imdlib masking check for this year
        d = imdlib.load("rain", year, year, source="archive", cache_dir=str(C.IMD_CACHE_DIR), offline=True,
                        progress=False)
        v = d.get_xarray()["rain"].values                                 # (time, lat, lon)
        rawA = A.astype(np.float64)
        n_sent = int((rawA == -999.0).sum())
        n_nan = int(np.isnan(v).sum())
        same = np.allclose(v[~np.isnan(v)], rawA[~np.isnan(v)])
        mask_rows.append({"year": year, "raw_minus999_cells": n_sent, "imdlib_nan_cells": n_nan,
                          "nan_equals_minus999": n_nan == n_sent and bool(np.isnan(v[rawA == -999.0]).all()),
                          "unmasked_values_identical_to_raw": bool(same),
                          "raw_unique_negatives": str(sorted(set(np.unique(rawA[rawA < 0]).round(3).tolist())))})

    cs = pd.DataFrame(rows)
    log("\nCASES (rain cells overlapping the old district, 1 Jun-30 Sep; raw bytes):")
    show = ["district", "year", "why", "gridded_R_season_mm", "district_median_mm", "max_daily_cell_mm", "max_cell_date",
            "cell_days_gt_300", "cells_with_day_gt_300", "sentinel_minus999", "other_negative", "values_gt_1000",
            "days_all_cells_zero", "median_days_all_zero_other_years", "cell_season_total_min_mm",
            "cell_season_total_max_mm", "gridded_subdivision_total_mm", "imd_subdivision_total_mm",
            "ratio_gridded_sub_over_imd"]
    log(cs[show].T.to_string(float_format=lambda x: f"{x:.1f}"))
    table(cs, "cases")
    mk = pd.DataFrame(mask_rows).drop_duplicates("year")
    log("\nimdlib missing-value handling (get_xarray vs raw bytes):")
    log(mk.to_string(index=False))
    table(mk, "imdlib_masking")

    # Sentinel scan over all years for all cells overlapping any old district
    scan = []
    for yy in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1):
        B = cache.get(yy, None)
        B = raw_rain(yy) if B is None else B
        cells = B[:, w.drop_duplicates(["ilat", "ilon"]).ilat.to_numpy(), w.drop_duplicates(["ilat", "ilon"]).ilon.to_numpy()]
        scan.append({"year": yy, "cell_days": cells.size, "minus999": int((cells == -999).sum()),
                     "other_negative": int(((cells < 0) & (cells != -999)).sum()), "nan": int(np.isnan(cells).sum()),
                     "gt_300": int((cells > 300).sum()), "gt_1000": int((cells > 1000).sum()),
                     "max_mm": float(np.nanmax(np.where(cells == -999, np.nan, cells)))})
    sc = pd.DataFrame(scan)
    log("\nSentinel scan, all cells overlapping Maharashtra old districts, all days:")
    log(sc.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    table(sc, "sentinel_scan")

    bug = (cs.sentinel_minus999.sum() + cs.other_negative.sum() + cs.nan_in_raw.sum() + cs.values_gt_1000.sum() > 0
           or not mk.nan_equals_minus999.all() or not mk.unmasked_values_identical_to_raw.all()
           or sc[["minus999", "other_negative", "nan", "gt_1000"]].to_numpy().sum() > 0)
    log("\nVERDICT (A13.4b/c): " + ("POSSIBLE PROCESSING ISSUE - sentinel/fill values or masking mismatch found; "
                                    "inspect before building." if bug else
                                    "No sentinel, fill, NaN or impossible values in the cells used, and imdlib's masking "
                                    "matches the raw bytes. The anomalies are values present in the IMD product "
                                    "itself (property of the data), so A13.4c applies: keep all districts, add dq_flag."))

    # dq_flag table (rule A13.4c) for both panels
    flags = pd.concat([rz.assign(panel="13"), rzw[~rzw.district.isin(p.district.unique())].assign(panel="wide_extra")])
    flags["dq_flag"] = flags.screen_flag.astype(int)
    flags[["district", "year", "robust_z", "dq_flag"]].drop_duplicates(["district", "year"]).to_csv(C.DQ_FLAGS_FILE, index=False)
    log(f"dq_flag table -> {C.DQ_FLAGS_FILE.relative_to(C.ROOT)}: {int(flags.dq_flag.sum())} flagged district-years "
        f"({flags[flags.dq_flag == 1][['district', 'year']].values.tolist()})")
    if "dq_flag" in p.columns:
        chk = p.merge(flags[["district", "year", "dq_flag"]], on=["district", "year"], suffixes=("", "_05c"))
        assert (chk.dq_flag == chk.dq_flag_05c).all(), "panel dq_flag differs from the 05c screen"
        log("Check: panel_final.csv dq_flag equals the 05c screen (same rule).")
    log(HEAD)
    logf.close()


if __name__ == "__main__":
    main()
