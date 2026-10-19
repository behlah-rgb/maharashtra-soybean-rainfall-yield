"""Step 5: build the final district-level panel from gridded data. SKELETON ONLY - NOT YET RUN.

Waits for data from the teammate (see docs/HANDOFF.md):
  - ERA5-Land monthly NetCDF (2m temperature, total precipitation)  -> read_era5_land_monthly
  - IMD 0.25 degree gridded daily rainfall                           -> read_imd_rain_grid
  - district boundary file (current districts)                       -> dissolve_to_icrisat_districts
  - old-to-new district notes (which current districts form each
    ICRISAT district)                                                -> dissolve_to_icrisat_districts
  - optional irrigation data                                         -> (later control; not in this file)

Output: config.PANEL_FINAL_FILE with exactly the columns of panel_v1.csv (same names, same units) plus
temperature columns; and config.PANEL_FINAL_WIDE_FILE with the same columns for the wider robustness
district set (13 + config.ROBUST_EXTRA_DISTRICTS, built from data/processed/soy_clean_wide.csv). `subdivision` is kept for reference only; rainfall now comes from district polygons.

Extra packages needed (NOT installed; ask the user before adding to requirements.txt):
xarray + netCDF4 (NetCDF), geopandas + shapely (polygons), and possibly regionmask or rioxarray
(cell-in-polygon weights). The IMD binary .grd format may also need imdlib or a custom reader.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

# Same columns as panel_v1.csv, then temperature columns (deg C, district means over grid cells).
PANEL_V1_COLS = ["district", "dist_code", "subdivision", "year", "trend",
                 "area_kha", "prod_kt", "yield_kgha", "ln_yield",
                 "R_season", "R_early", "R_late", "R_julsep"]
TEMP_COLS = ["T_season", "T_early", "T_late"]


def read_era5_land_monthly(path: Path, variables=("t2m", "tp")):
    """Read ERA5-Land monthly-averaged NetCDF and return monthly fields in project units.

    Parameters
    ----------
    path : Path to the NetCDF file(s) under config.GRIDS_DIR.
    variables : ERA5-Land short names to read (t2m = 2m temperature, tp = total precipitation).

    Returns
    -------
    xarray.Dataset with dims (time, latitude, longitude):
      t2m in degrees Celsius (converted from Kelvin: C = K - 273.15; assert the `units`
      attribute is "K" before converting);
      tp in mm per month.

    Notes
    -----
    - Precipitation units MUST be read from the variable's `units` attribute, never assumed.
      ERA5-Land "monthly averaged reanalysis" stores tp as a MEAN DAILY total in metres
      (m per day), so the monthly total in mm = tp * 1000 * days_in_month(time). Confirm this
      from the attributes and the dataset's product type; if the file is "monthly averaged
      reanalysis by hour of day" or hourly accumulations, the conversion is different.
      Assert the converted Jun-Sep totals are of the same order as the IMD subdivision totals.
    - Check the time coordinate name (`time` vs `valid_time`) and that coverage is 2000-2017.
    - Check longitude convention (0-360 vs -180-180) before masking with polygons.
    """
    raise NotImplementedError("skeleton: waiting for ERA5-Land monthly NetCDF")


def read_imd_rain_grid(path: Path, years=range(C.YEAR_START, C.YEAR_END_TARGET + 1)):
    """Read IMD 0.25 x 0.25 degree gridded daily rainfall and aggregate to monthly totals.

    Parameters
    ----------
    path : directory or file(s) under config.GRIDS_DIR (IMD binary .grd per year, or NetCDF).
    years : years to read (default config.YEAR_START..config.YEAR_END_TARGET).

    Returns
    -------
    xarray.DataArray (time = month, lat, lon) of monthly rainfall totals in mm.

    Notes
    -----
    - IMD daily rainfall is in mm/day. Missing/ocean cells use a fill value (commonly -999);
      mask them before summing and assert no land cell in Maharashtra is missing in any month.
    - The 0.25 degree grid is 135 x 129 cells (lon 66.5-100.0E, lat 6.5-38.5N). Verify the
      dimensions and the leap-year day count when reading the binary format.
    """
    raise NotImplementedError("skeleton: waiting for IMD 0.25 degree grids")


CROSSWALK_STATUSES = ("CONFIRMED_OFFICIAL_PAGE", "CAVEAT", "UNVERIFIED")


def crosswalk_table() -> pd.DataFrame:
    """Old-to-new district crosswalk from config.DISTRICT_CROSSWALK (SPEC A10). Implemented (not a
    skeleton): it needs no gridded data. Columns: current_district, icrisat_district, status, note."""
    cw = pd.DataFrame(C.DISTRICT_CROSSWALK, columns=["current_district", "icrisat_district", "status", "note"])
    bad = set(cw.status) - set(CROSSWALK_STATUSES)
    assert not bad, f"unknown crosswalk status: {bad}"
    assert not cw.current_district.duplicated().any(), "a current district appears twice in the crosswalk"
    known = {d for ds in C.DISTRICT_SUBDIVISION.values() for d in ds}
    unknown = set(cw.icrisat_district) - known
    assert not unknown, f"crosswalk targets not in the ICRISAT district map: {unknown}"
    return cw


def check_crosswalk(current_districts, panel_districts) -> pd.DataFrame:
    """Guard for writing panel_final.csv (SPEC A10). Implemented (not a skeleton).

    current_districts : district names in the boundary file (current boundaries).
    panel_districts   : ICRISAT districts in the panel being written.
    A current district maps to itself if its name is an ICRISAT district; otherwise it needs a
    crosswalk row. Returns the rows used (current district -> panel district). Raises if a current
    district is unmapped, or if any row used for a panel district has status UNVERIFIED.
    CAVEAT rows are allowed but returned so the caller can log them.
    """
    cw = crosswalk_table().set_index("current_district")
    known = {d for ds in C.DISTRICT_SUBDIVISION.values() for d in ds}
    used, unmapped = [], []
    for cur in current_districts:
        if cur in cw.index:
            r = cw.loc[cur]
            used.append({"current_district": cur, "icrisat_district": r.icrisat_district, "status": r.status,
                         "note": r.note})
        elif cur in known:
            used.append({"current_district": cur, "icrisat_district": cur, "status": "SAME_NAME", "note": ""})
        else:
            unmapped.append(cur)
    if unmapped:
        raise ValueError(f"current districts with no ICRISAT parent (add them to config.DISTRICT_CROSSWALK): "
                         f"{sorted(unmapped)}")
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


def dissolve_to_icrisat_districts(boundaries_path: Path, old_new_map_path: Path):
    """Dissolve current district polygons into the older ICRISAT district boundaries.

    Parameters
    ----------
    boundaries_path : current district boundary file (shapefile / GeoJSON / GeoPackage).
    old_new_map_path : optional CSV override; by default the crosswalk is config.DISTRICT_CROSSWALK
        via crosswalk_table() (SPEC A10). Statuses: CONFIRMED_OFFICIAL_PAGE (Latur->Osmanabad,
        Gadchiroli->Chandrapur, Nandurbar->Dhule, Hingoli->Parbhani, Gondia->Bhandara,
        Jalna->Aurangabad, Palghar->Thane; source: official district-history pages cited in the
        teammate's report, not independently verified), CAVEAT (Washim->Akola needs taluka-level
        confirmation; Jalna's Partur taluka came from Parbhani), UNVERIFIED (everything else,
        e.g. Mumbai Suburban->Bombay and the 2023-24 renames). Call check_crosswalk() before
        dissolving; it refuses only if a pair used for a panel district is UNVERIFIED.

    Returns
    -------
    geopandas.GeoDataFrame with one polygon per ICRISAT district, column `district` spelled
    exactly as in ICRISAT (e.g. "Amarawati", "Yeotmal").

    Notes
    -----
    - Fail loudly if any current Maharashtra district is unmapped, or if any of the selected
      ICRISAT districts in data/processed/soy_clean.csv has no polygon.
    - Reproject to an equal-area CRS before any area check. Compare dissolved areas with
      known district areas as a sanity check.
    """
    raise NotImplementedError("skeleton: waiting for boundary file and old-to-new notes")


def district_average(grid, districts, weights: str = "area"):
    """Average grid cells inside each district polygon.

    Parameters
    ----------
    grid : xarray.DataArray (time, lat, lon) from read_imd_rain_grid or read_era5_land_monthly.
    districts : GeoDataFrame from dissolve_to_icrisat_districts.
    weights : "area" = weight each cell by the fraction of its area inside the polygon
        (times cos(latitude) for cell area). "centroid" = include cells whose centre falls inside.
        Area weights are preferred because small districts may contain few 0.25 degree cells
        (and ERA5-Land is 0.1 degree).

    Returns
    -------
    pandas.DataFrame with columns district, year, month, value (district mean).

    Notes
    -----
    - Assert every district gets at least one cell, and report the cell count per district.
    - A future option is to weight by soybean area (a crop mask) rather than land area.
    """
    raise NotImplementedError("skeleton")


def seasonal_windows(monthly: pd.DataFrame, how: str):
    """Collapse district-month values to district-year windows.

    Parameters
    ----------
    monthly : output of district_average (district, year, month, value).
    how : "sum" for rainfall (mm) -> R_season, R_early, R_late, R_julsep (config.MONTHS_JULSEP);
          "mean" for temperature (deg C) -> T_season, T_early, T_late.
          Windows come from config.MONTHS_SEASON / MONTHS_EARLY / MONTHS_LATE.

    Returns
    -------
    pandas.DataFrame: district, year, and the three window columns.
    """
    raise NotImplementedError("skeleton")


def build_panel_final(rain: pd.DataFrame, temp: pd.DataFrame) -> pd.DataFrame:
    """Join soy_clean.csv with gridded rainfall and temperature, and write panel_final.csv.

    Parameters
    ----------
    rain : district-year R_season, R_early, R_late, R_julsep (mm) from the IMD grid.
    temp : district-year T_season, T_early, T_late (deg C) from ERA5-Land.

    Returns
    -------
    pandas.DataFrame with columns PANEL_V1_COLS + TEMP_COLS, years YEAR_START..YEAR_END_TARGET,
    written to config.PANEL_FINAL_FILE (13 districts) and config.PANEL_FINAL_WIDE_FILE (wider set).

    Notes
    -----
    - Same definitions as src/02: ln_yield = log(yield_kgha), trend = year - TREND_BASE_YEAR.
    - Assert rows = districts x years, no missing values, and unique (district, year).
    - Cross-check: for 2000-2015, the district rainfall averaged within each subdivision should
      correlate strongly with the IMD subdivision series in panel_v1.csv; report the correlation.
    """
    raise NotImplementedError("skeleton")


def main() -> None:
    raise NotImplementedError("src/05 is a skeleton; do not run until the gridded data has arrived "
                              "(see docs/HANDOFF.md)")


if __name__ == "__main__":
    main()
