"""Step 5: build the final district-level panel from IMD gridded data and 2011 Census boundaries.

Reads  : config.BOUNDARY_DIR/2011_Dist.shp (DataMeet), config.IMD_CACHE_DIR (imdlib cache, src/05a),
         config.SOY_CLEAN_FILE, config.SOY_CLEAN_WIDE_FILE, config.DISTRICT_MAP_FILE
Writes : config.OLD_TO_CURRENT_FILE (data/interim/old_to_current_districts.csv)
         config.OLD_DISTRICTS_GPKG (data/interim/old_districts.gpkg)
         config.CELL_WEIGHTS_FILE (data/interim/grid_cell_weights.csv)
         config.OLD_DISTRICT_WEATHER_FILE (all 26 old districts x 18 years, incl. coverage diagnostics)
         config.PANEL_FINAL_FILE (13 districts x 18 years) and config.PANEL_FINAL_WIDE_FILE (17 x 18)

Method (SPEC A12.4): fractional overlap. For each grid cell (lon-lat box around the cell centre) and each
old district polygon, weight = overlap area in an equal-area projection (config.EQUAL_AREA_CRS). Daily
district value = weighted mean over cells with valid data that day (weights renormalised). If no
overlapping cell is valid on a day, the nearest valid cell centre (to the district's representative
point) is used and counted. Same method for 0.25 deg rainfall and 1.0 deg temperature; with 1.0 deg cells
every touching cell contributes by its overlap share, so districts with few cell centres still get values.
Variables (SPEC A12.5): R_season, R_early, R_late, R_julsep (mm), dry_spell_max (days with district-mean
rain < DRY_DAY_MM, longest run in 1 Jun-30 Sep), T_season (mean of daily (Tmax + Tmin)/2, deg C),
dq_flag (SPEC A13.4c: |R_season - district median| > 3 robust SD; diagnosis in src/05c).
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

PANEL_V1_COLS = ["district", "dist_code", "subdivision", "year", "trend",
                 "area_kha", "prod_kt", "yield_kgha", "ln_yield",
                 "R_season", "R_early", "R_late", "R_julsep"]
NEW_COLS = ["dry_spell_max", "T_season", "dq_flag"]
WEATHER_COLS = ["R_season", "R_early", "R_late", "R_julsep", "dry_spell_max", "T_season"]
CROSSWALK_STATUSES = ("CONFIRMED_OFFICIAL_PAGE", "CAVEAT", "ALIAS_NAME_ONLY", "UNVERIFIED")


# ---- Crosswalk (SPEC A10/A11/A12.3) --------------------------------------------------------------
def icrisat_names() -> set:
    return {d for ds in C.DISTRICT_SUBDIVISION.values() for d in ds}


def crosswalk_table() -> pd.DataFrame:
    """Old-to-new district crosswalk from config.DISTRICT_CROSSWALK."""
    cw = pd.DataFrame(C.DISTRICT_CROSSWALK, columns=["current_district", "icrisat_district", "status", "note"])
    bad = set(cw.status) - set(CROSSWALK_STATUSES)
    assert not bad, f"unknown crosswalk status: {bad}"
    assert not cw.current_district.duplicated().any(), "a current district appears twice in the crosswalk"
    unknown = set(cw.icrisat_district) - icrisat_names()
    assert not unknown, f"crosswalk targets not in the ICRISAT district map: {unknown}"
    return cw


def canonical(name: str) -> str:
    """Boundary-layer or normals-file spelling -> canonical name (approved variants only)."""
    n = " ".join(str(name).strip().split()).title()
    return C.SPELLING_VARIANTS.get(n, n)


def check_crosswalk(current_districts, panel_districts) -> pd.DataFrame:
    """Guard for writing panel_final.csv. current_districts: canonical names of the boundary layer.
    Raises if a current district is unmapped, a panel district has no polygon, or a row used for a
    panel district is UNVERIFIED. ALIAS_NAME_ONLY and CAVEAT never block (CAVEAT rows are returned)."""
    cw = crosswalk_table().set_index("current_district")
    used, unmapped = [], []
    for cur in current_districts:
        if cur in cw.index:
            r = cw.loc[cur]
            used.append({"current_district": cur, "icrisat_district": r.icrisat_district, "status": r.status,
                         "note": r.note})
        elif cur in icrisat_names():
            used.append({"current_district": cur, "icrisat_district": cur, "status": "SAME_DISTRICT", "note": ""})
        else:
            unmapped.append(cur)
    if unmapped:
        raise ValueError(f"current districts with no ICRISAT parent: {sorted(unmapped)}")
    u = pd.DataFrame(used)
    u = u[u.icrisat_district.isin(set(panel_districts))]
    missing = set(panel_districts) - set(u.icrisat_district)
    if missing:
        raise ValueError(f"panel districts with no polygon in the boundary file: {sorted(missing)}")
    blocked = u[u.status == "UNVERIFIED"]
    if len(blocked):
        raise ValueError("REFUSED to write panel_final.csv: UNVERIFIED crosswalk pairs are used:\n"
                         + blocked.to_string(index=False))
    return u


def load_current_districts():
    """Maharashtra districts of the DataMeet 2011 layer with canonical names. Stops on any unmatched name."""
    import geopandas as gpd
    g = gpd.read_file(C.BOUNDARY_DIR / (Path(C.DATAMEET_LAYER).name + ".shp"))
    g = g[g.ST_NM.str.strip().str.lower() == C.STATE_NAME_BOUNDARY.lower()].copy()
    assert len(g) == C.EXPECTED_N_CURRENT_DISTRICTS, f"{len(g)} Maharashtra districts, expected 35"
    assert g.is_valid.all(), "invalid geometries"
    g["layer_name"] = g.DISTRICT.str.strip()
    g["current_district"] = g.layer_name.map(canonical)
    known = icrisat_names() | set(crosswalk_table().current_district)
    bad = sorted(set(g.current_district) - known)
    if bad:
        sys.exit(f"STOP: boundary names that match no ICRISAT district and no crosswalk row: {bad}")
    assert not g.current_district.duplicated().any(), "two polygons map to the same canonical name"
    renamed = g[g.layer_name.str.title() != g.current_district]
    print("Name variants applied (layer -> canonical): "
          + ", ".join(f"{a} -> {b}" for a, b in zip(renamed.layer_name, renamed.current_district)))
    return g


def alias_sanity_check(g) -> None:
    """SPEC A11.2: if the layer uses new (alias) names, compare each such polygon's area and centroid with
    the old-name polygon of the 2011 Census layer. The 2011 layer itself uses the old names."""
    aliases = crosswalk_table().query("status == 'ALIAS_NAME_ONLY'")
    used = g[g.current_district.isin(aliases.current_district)]
    if used.empty:
        print("Alias sanity check (A11.2): not applicable, the layer uses the old names "
              f"({', '.join(aliases.icrisat_district)}).")
        return
    raise NotImplementedError("alias names present: compare area and centroid with the 2011 Census polygons")


def build_crosswalk_and_dissolve(g):
    cw = crosswalk_table().set_index("current_district")
    rows = []
    for r in g.itertuples():
        if r.current_district in cw.index:
            c = cw.loc[r.current_district]
            parent, status, note = c.icrisat_district, c.status, c.note
        else:
            parent, status, note = r.current_district, "SAME_DISTRICT", "maps to itself"
        rows.append({"old_icrisat_district": parent, "current_district": r.current_district,
                     "layer_name": r.layer_name, "census2011_code": r.censuscode, "status": status,
                     "note": note,
                     "source": C.CROSSWALK_SOURCE_OVERRIDES.get(r.current_district, C.CROSSWALK_SOURCE_NOTE)})
    xw = pd.DataFrame(rows).sort_values(["old_icrisat_district", "current_district"])
    assert set(xw.old_icrisat_district) == icrisat_names(), \
        f"old districts without polygons: {icrisat_names() - set(xw.old_icrisat_district)}"
    print("Palghar: not in the 2011 layer (created 2014), so Thane = Thane only.")
    xw.to_csv(C.OLD_TO_CURRENT_FILE, index=False)
    print(f"Saved {C.OLD_TO_CURRENT_FILE.relative_to(C.ROOT)} ({len(xw)} current districts -> "
          f"{xw.old_icrisat_district.nunique()} old districts)")
    multi = xw.groupby("old_icrisat_district").current_district.agg(list)
    for k, v in multi[multi.str.len() > 1].items():
        print(f"  {k} = {' + '.join(v)}")

    ea = g.to_crs(C.EQUAL_AREA_CRS)
    ea["area_km2_current"] = ea.area / 1e6
    ea = ea.merge(xw[["current_district", "old_icrisat_district"]], on="current_district")
    old = ea.dissolve(by="old_icrisat_district", aggfunc={"area_km2_current": "sum"}).reset_index()
    old["area_km2"] = old.area / 1e6
    old["members"] = old.old_icrisat_district.map(multi.str.join(" + "))
    old = old.rename(columns={"old_icrisat_district": "district"})
    m = pd.read_csv(C.DISTRICT_MAP_FILE).set_index("district").subdivision
    old["subdivision"] = old.district.map(m)
    assert np.allclose(old.area_km2, old.area_km2_current, rtol=1e-3), "dissolved area != sum of member areas"
    out = old[["district", "subdivision", "members", "area_km2", "geometry"]].to_crs("EPSG:4326")
    C.OLD_DISTRICTS_GPKG.unlink(missing_ok=True)
    out.to_file(C.OLD_DISTRICTS_GPKG, driver="GPKG")
    print(f"Saved {C.OLD_DISTRICTS_GPKG.relative_to(C.ROOT)}. Old district areas (km2, {C.EQUAL_AREA_CRS}):")
    print(out.drop(columns="geometry").sort_values("district").to_string(index=False, float_format=lambda x: f"{x:,.0f}"))
    return out, xw


# ---- Grid weights ---------------------------------------------------------------------------
def cell_weights(old, var: str):
    """Overlap area (km2) of each grid cell with each old district, plus a cell-centre-inside flag."""
    import geopandas as gpd
    from shapely import box, segmentize
    from imdlib.util import ARCHIVE_GRID, GRIDS
    grid = GRIDS[ARCHIVE_GRID[var]]
    xmin, ymin, xmax, ymax = old.total_bounds
    h = grid.step / 2
    lons = grid.lon[(grid.lon >= xmin - grid.step) & (grid.lon <= xmax + grid.step)]
    lats = grid.lat[(grid.lat >= ymin - grid.step) & (grid.lat <= ymax + grid.step)]
    LO, LA = np.meshgrid(lons, lats)
    cells = gpd.GeoDataFrame({"lon": LO.ravel(), "lat": LA.ravel()},
                             geometry=[segmentize(box(x - h, y - h, x + h, y + h), 0.05)
                                       for x, y in zip(LO.ravel(), LA.ravel())], crs="EPSG:4326")
    cells["ilon"] = np.rint((cells.lon - grid.lon0) / grid.step).astype(int)
    cells["ilat"] = np.rint((cells.lat - grid.lat0) / grid.step).astype(int)
    cells_ea = cells.to_crs(C.EQUAL_AREA_CRS)
    cells_ea["cell_km2"] = cells_ea.area / 1e6
    old_ea = old.to_crs(C.EQUAL_AREA_CRS)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ov = gpd.overlay(cells_ea, old_ea[["district", "geometry"]], how="intersection", keep_geom_type=True)
    ov["overlap_km2"] = ov.area / 1e6
    ov = ov[ov.overlap_km2 > 1e-6]
    centres = gpd.GeoDataFrame(cells[["lon", "lat"]], geometry=gpd.points_from_xy(cells.lon, cells.lat),
                               crs="EPSG:4326")
    inside = gpd.sjoin(centres, old[["district", "geometry"]], predicate="within")[["lon", "lat", "district"]]
    inside["centre_inside"] = True
    w = ov[["district", "lon", "lat", "ilon", "ilat", "cell_km2", "overlap_km2"]].merge(
        inside, on=["district", "lon", "lat"], how="left")
    w["centre_inside"] = w.centre_inside.eq(True)
    w["frac_of_cell"] = w.overlap_km2 / w.cell_km2
    w.insert(0, "grid", f"{var}_{grid.step}deg")
    # check: overlap areas add up to each district's area
    tot = w.groupby("district").overlap_km2.sum()
    area = old.set_index("district").area_km2
    assert np.allclose(tot[area.index], area, rtol=5e-3), f"{var}: overlap areas do not sum to district areas"
    return w, cells


def daily_district_means(var: str, year: int, w: pd.DataFrame, cells: pd.DataFrame, old):
    """(DataFrame time x district of daily means, diagnostics per district, units attribute)."""
    import imdlib
    d = imdlib.load(var, year, year, source="archive", cache_dir=str(C.IMD_CACHE_DIR), offline=True, progress=False)
    ds = d.get_xarray()
    v = ds[list(ds.data_vars)[0]]
    assert v.dims == ("time", "lat", "lon")
    arr = v.values                                             # (time, lat, lon); NaN = IMD missing value
    times = pd.DatetimeIndex(v.time.values)
    out, diag = {}, {}
    pts = old.to_crs(C.EQUAL_AREA_CRS).representative_point().to_crs("EPSG:4326")
    for i, dist in enumerate(old.district):
        wd = w[w.district == dist]
        X = arr[:, wd.ilat.to_numpy(), wd.ilon.to_numpy()]     # days x cells
        valid = np.isfinite(X)
        wt = wd.overlap_km2.to_numpy()
        den = valid.astype(float) @ wt
        num = np.where(valid, X, 0.0) @ wt
        with np.errstate(invalid="ignore", divide="ignore"):
            val = num / den
        share = den / wt.sum()
        nearest_days = 0
        if (den == 0).any():
            p = pts.iloc[i]
            order = cells.assign(dd=(cells.lon - p.x) ** 2 + (cells.lat - p.y) ** 2).sort_values("dd")
            for t in np.flatnonzero(den == 0):
                for c in order.itertuples():
                    x = arr[t, c.ilat, c.ilon]
                    if np.isfinite(x):
                        val[t] = x
                        nearest_days += 1
                        break
        assert np.isfinite(val).all(), f"{var} {year} {dist}: days without any value"
        out[dist] = val
        diag[dist] = {"min_valid_area_share": float(share.min()), "mean_valid_area_share": float(share.mean()),
                      "nearest_cell_days": nearest_days, "n_cells": len(wd),
                      "n_centres_inside": int(wd.centre_inside.sum())}
    return pd.DataFrame(out, index=times), diag, v.attrs.get("units")


def dq_flag(p: pd.DataFrame) -> pd.Series:
    """SPEC A13.4c: 1 if |R_season - district median| > DQ_ROBUST_Z x 1.4826 x MAD (within district)."""
    g = p.groupby("district").R_season
    med = g.transform("median")
    mad = g.transform(lambda s: np.median(np.abs(s - s.median())))
    return ((p.R_season - med).abs() > C.DQ_ROBUST_Z * 1.4826 * mad).astype(int)


def longest_run(mask: np.ndarray) -> int:
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def season_slice(df: pd.DataFrame, year: int, start: str, end: str) -> pd.DataFrame:
    return df.loc[f"{year}-{start}":f"{year}-{end}"]


def main() -> None:
    print("1. Boundaries and crosswalk")
    g = load_current_districts()
    alias_sanity_check(g)
    old, xw = build_crosswalk_and_dissolve(g)
    soy = pd.read_csv(C.SOY_CLEAN_FILE)
    wide = pd.read_csv(C.SOY_CLEAN_WIDE_FILE)
    for nm, dset in [("13-district", soy), ("17-district wide", wide)]:
        used = check_crosswalk(g.current_district, sorted(dset.district.unique()))
        print(f"Crosswalk guard ({nm} panel): PASSED. Statuses used: {used.status.value_counts().to_dict()}")
        for r in used[used.note.str.contains("CAVEAT", na=False) | (used.status == "CAVEAT")].itertuples():
            print(f"  caveat logged: {r.current_district} -> {r.icrisat_district}: {r.note}")

    print("\n2. Grid-cell weights (fractional overlap)")
    W, CELLS = {}, {}
    for var in C.IMD_VARS:
        W[var], CELLS[var] = cell_weights(old, var)
    allw = pd.concat(W.values(), ignore_index=True)
    allw.to_csv(C.CELL_WEIGHTS_FILE, index=False)
    print(f"Saved {C.CELL_WEIGHTS_FILE.relative_to(C.ROOT)}")
    summ = allw[allw.grid.str.startswith(("rain", "tmax"))].groupby(["district", "grid"]).agg(
        n_cells=("lon", "size"), n_centres_inside=("centre_inside", "sum")).unstack("grid")
    print("Cells per old district (overlapping cells; cell centres inside the polygon):")
    print(summ.to_string())

    print("\n3. Daily district means and seasonal variables")
    rows, diag_rows, units = [], [], {}
    s, e, ee = C.SEASON_START_MMDD, C.SEASON_END_MMDD, C.EARLY_END_MMDD
    for year in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1):
        daily = {}
        for var in C.IMD_VARS:
            daily[var], diag, units[var] = daily_district_means(var, year, W[var], CELLS[var], old)
            for dist, dg in diag.items():
                diag_rows.append({"district": dist, "year": year, "var": var, **dg})
        rain = season_slice(daily["rain"], year, s, e)
        assert len(rain) == 122, f"season length {len(rain)}"
        early = season_slice(daily["rain"], year, s, ee)
        late = season_slice(daily["rain"], year, "08-01", e)
        julsep = season_slice(daily["rain"], year, "07-01", e)
        tx, tn = season_slice(daily["tmax"], year, s, e), season_slice(daily["tmin"], year, s, e)
        assert len(tx) == len(tn) == 122
        tmean = (tx + tn) / 2
        for dist in old.district:
            rows.append({"district": dist, "year": year, "R_season": rain[dist].sum(), "R_early": early[dist].sum(),
                         "R_late": late[dist].sum(), "R_julsep": julsep[dist].sum(),
                         "dry_spell_max": longest_run(rain[dist].to_numpy() < C.DRY_DAY_MM),
                         "T_season": tmean[dist].mean(), "Tmax_season": tx[dist].mean(),
                         "Tmin_season": tn[dist].mean(),
                         "rain_days_ge_2p5": int((rain[dist].to_numpy() >= C.DRY_DAY_MM).sum())})
        print(f"  {year} done")
    print(f"Units attributes from imdlib: {units}")
    wx = pd.DataFrame(rows)
    dg = pd.DataFrame(diag_rows)
    piv = dg.pivot_table(index=["district", "year"], columns="var",
                         values=["min_valid_area_share", "nearest_cell_days"], aggfunc="first")
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    wx = wx.merge(piv.reset_index(), on=["district", "year"])
    wx["subdivision"] = wx.district.map(old.set_index("district").subdivision)
    assert np.allclose(wx.R_early + wx.R_late, wx.R_season), "R_early + R_late != R_season"
    assert wx[WEATHER_COLS].notna().all().all()
    wx.to_csv(C.OLD_DISTRICT_WEATHER_FILE, index=False)
    print(f"Saved {C.OLD_DISTRICT_WEATHER_FILE.relative_to(C.ROOT)}: {len(wx)} rows "
          f"({wx.district.nunique()} old districts x {wx.year.nunique()} years)")
    print(f"Nearest-cell fallback days, total by variable: {dg.groupby('var').nearest_cell_days.sum().to_dict()}")
    print(f"Minimum daily valid-area share by variable: "
          f"{dg.groupby('var').min_valid_area_share.min().round(3).to_dict()}")

    print("\n4. Panels")
    dmap = pd.read_csv(C.DISTRICT_MAP_FILE).set_index("district").subdivision
    for src, dest, n_d in [(C.SOY_CLEAN_FILE, C.PANEL_FINAL_FILE, 13),
                           (C.SOY_CLEAN_WIDE_FILE, C.PANEL_FINAL_WIDE_FILE, 17)]:
        sc = pd.read_csv(src)
        sc = sc[sc.year.between(C.YEAR_START, C.YEAR_END_TARGET)]
        p = sc.drop(columns=["subdivision", "yield_implied"]).merge(
            wx[["district", "year"] + WEATHER_COLS], on=["district", "year"], how="left", validate="one_to_one")
        p["subdivision"] = p.district.map(dmap)
        p["ln_yield"] = np.log(p.yield_kgha)
        p["trend"] = p.year - C.TREND_BASE_YEAR
        p["dq_flag"] = dq_flag(p)
        print(f"  dq_flag (A13.4c) = 1 for: {p.loc[p.dq_flag == 1, ['district', 'year']].values.tolist()}")
        p = p[PANEL_V1_COLS + NEW_COLS].sort_values(["district", "year"]).reset_index(drop=True)
        n_t = C.YEAR_END_TARGET - C.YEAR_START + 1
        assert p.district.nunique() == n_d and len(p) == n_d * n_t, f"{dest.name}: {len(p)} rows != {n_d} x {n_t}"
        assert not p.duplicated(["district", "year"]).any(), "duplicate keys"
        na = p.isna().sum()
        assert na.sum() == 0, f"missing values:\n{na[na > 0]}"
        p.to_csv(dest, index=False)
        print(f"Saved {dest.relative_to(C.ROOT)}: {len(p)} rows = {n_d} x {n_t}, no missing values, unique keys")
    p = pd.read_csv(C.PANEL_FINAL_FILE)
    print(p.describe().T[["mean", "std", "min", "max"]].to_string(float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
