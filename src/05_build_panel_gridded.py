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


def dissolve_to_icrisat_districts(boundaries_path: Path, old_new_map_path: Path):
    """Dissolve current district polygons into the older ICRISAT district boundaries.

    Parameters
    ----------
    boundaries_path : current district boundary file (shapefile / GeoJSON / GeoPackage).
    old_new_map_path : CSV of (current_district, icrisat_district, status), built from the teammate's
        old-to-new district notes. UNVERIFIED candidate pairs (not yet confirmed by the teammate;
        SPEC A5): Washim -> Akola, Hingoli -> Parbhani, Gondia -> Bhandara, Nandurbar -> Dhule,
        Latur -> Osmanabad, Jalna -> Aurangabad/Parbhani, Palghar -> Thane, Mumbai Suburban -> Bombay.
        The CSV must carry status = UNVERIFIED for every pair until the teammate confirms it; the
        build must refuse to write panel_final.csv while any pair used by a selected district is
        UNVERIFIED. Record splits that crossed old district lines.

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
