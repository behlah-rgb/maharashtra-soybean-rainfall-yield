"""Step 5a: download raw weather grids (IMD via imdlib) and the 2011 Census district boundaries (DataMeet).

Reads  : nothing local except config.py
Writes : config.BOUNDARY_DIR/2011_Dist.{shp,shx,dbf,prj}   (DataMeet maps, pinned commit)
         config.IMD_CACHE_DIR/archive/{rain,tmax,tmin}/<year>.grd + manifest.json  (imdlib cache layout)
         config.DATA_SOURCES_DOC (docs/data_sources.md)
Never edits a raw file after download. Re-running reuses files already present with the right size.

API (verified in the installed imdlib 0.3.1 source and README, 2026-10-19):
  imdlib.load(var, start, end, source='archive', cache_dir=..., parallel=4) downloads missing yearly
  files by HTTP POST to https://imdpune.gov.in/cmpg/Griddata/{rainfall,maxtemp,mintemp}.php,
  checks each file's exact byte size, retries 3 times per file, and records url, POST data, size,
  sha256 and UTC download time in <cache_dir>/manifest.json. Grids (imdlib.util.GRIDS):
  rain 0.25 deg, 135 x 129 cells, first centre 66.5E 6.5N; tmax/tmin 1.0 deg, 31 x 31, first
  centre 67.5E 7.5N. Missing values: rain -999, temperature 99.9 (NaN in get_xarray()).
Failure rule (SPEC A12.2): at most DOWNLOAD_MAX_ATTEMPTS imdlib.load calls per variable; if all fail,
stop with an error and substitute nothing.
"""
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

import imdlib  # noqa: E402
from imdlib.util import ARCHIVE_GRID, ARCHIVE_URLS, GRIDS  # noqa: E402

UNITS = {"rain": "mm/day", "tmax": "deg C", "tmin": "deg C"}
PRODUCT = {"rain": "IMD daily gridded rainfall (Pai et al. 2014), 0.25 deg",
           "tmax": "IMD daily gridded maximum temperature, 1.0 deg",
           "tmin": "IMD daily gridded minimum temperature, 1.0 deg"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_boundaries() -> list:
    """Download the DataMeet 2011 district shapefile parts (pinned commit). Two attempts per file."""
    C.BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for ext in C.DATAMEET_EXTS:
        name = Path(C.DATAMEET_LAYER).name + ext
        url = f"https://raw.githubusercontent.com/{C.DATAMEET_REPO}/{C.DATAMEET_COMMIT}/{C.DATAMEET_LAYER}{ext}"
        dest = C.BOUNDARY_DIR / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  boundary {name}: already present ({dest.stat().st_size:,} bytes), not re-downloaded")
            when = datetime.fromtimestamp(dest.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            for attempt in range(1, C.DOWNLOAD_MAX_ATTEMPTS + 1):
                try:
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                        f.write(r.read())
                    tmp.rename(dest)
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"  boundary {name}: attempt {attempt} failed: {e}")
                    if attempt == C.DOWNLOAD_MAX_ATTEMPTS:
                        sys.exit(f"STOP: boundary download failed {attempt} times ({url}). "
                                 "Not substituting another source (SPEC A12.2).")
                    time.sleep(10)
            when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"  boundary {name}: downloaded {dest.stat().st_size:,} bytes")
        rows.append({"file": str(dest.relative_to(C.ROOT)), "url": url, "retrieved_utc": when,
                     "size": dest.stat().st_size, "sha256": sha256(dest)})
    return rows


def maharashtra_bounds():
    import geopandas as gpd
    g = gpd.read_file(C.BOUNDARY_DIR / (Path(C.DATAMEET_LAYER).name + ".shp"))
    print(f"  boundary layer: {len(g)} districts, columns {list(g.columns)}, CRS {g.crs}")
    st = [c for c in g.columns if c.upper() in ("ST_NM", "STATE", "ST_NAME", "STATE_NAME")]
    assert st, f"no state-name column in {list(g.columns)}"
    mh = g[g[st[0]].astype(str).str.strip().str.lower() == C.STATE_NAME_BOUNDARY.lower()]
    assert len(mh), "no Maharashtra rows in the boundary layer"
    return mh.to_crs("EPSG:4326").total_bounds, len(mh)


def download_imd() -> dict:
    out = {}
    for var in C.IMD_VARS:
        for attempt in range(1, C.DOWNLOAD_MAX_ATTEMPTS + 1):
            try:
                print(f"  imdlib.load('{var}', {C.WEATHER_YEAR_START}, {C.WEATHER_YEAR_END}) attempt {attempt}")
                d = imdlib.load(var, C.WEATHER_YEAR_START, C.WEATHER_YEAR_END, source="archive",
                                cache_dir=str(C.IMD_CACHE_DIR), progress=False, parallel=4)
                out[var] = d
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {var}: attempt {attempt} failed: {type(e).__name__}: {e}")
                if attempt == C.DOWNLOAD_MAX_ATTEMPTS:
                    sys.exit(f"STOP: IMD download of {var} failed {attempt} times. No substitute source is used "
                             "(NASA POWER for temperature only with the user's approval; SPEC A12.2).")
                time.sleep(30)
    return out


def check_grid(var: str, data, bounds) -> dict:
    """Grid extent from imdlib's grid definition and the first year's data (one year only, to keep
    memory small); check it covers Maharashtra. Every year's file size is checked exactly."""
    grid = GRIDS[ARCHIVE_GRID[var]]
    leap = lambda y: (y % 4 == 0 and y % 100 != 0) or y % 400 == 0  # noqa: E731
    for y in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1):
        path = C.IMD_CACHE_DIR / "archive" / var / f"{y}.grd"
        assert path.stat().st_size == grid.file_size(366 if leap(y) else 365), f"wrong size {path}"
    first = imdlib.load(var, C.WEATHER_YEAR_START, C.WEATHER_YEAR_START, source="archive",
                        cache_dir=str(C.IMD_CACHE_DIR), offline=True, progress=False)
    ds = first.get_xarray()
    lon, lat = ds.lon.values, ds.lat.values
    half = grid.step / 2
    ext = (lon.min() - half, lat.min() - half, lon.max() + half, lat.max() + half)
    xmin, ymin, xmax, ymax = bounds
    covers = ext[0] <= xmin and ext[1] <= ymin and ext[2] >= xmax and ext[3] >= ymax
    v = ds[list(ds.data_vars)[0]]
    box = v.sel(lon=slice(xmin - grid.step, xmax + grid.step), lat=slice(ymin - grid.step, ymax + grid.step))
    valid_cells = int(np.isfinite(box.isel(time=0)).sum())
    print(f"  {var}: grid {grid.step} deg, {grid.nlon} x {grid.nlat} cells; extent lon {ext[0]:.3f}-{ext[2]:.3f}, "
          f"lat {ext[1]:.3f}-{ext[3]:.3f}; Maharashtra bounds lon {xmin:.3f}-{xmax:.3f}, lat {ymin:.3f}-{ymax:.3f} "
          f"-> covers: {covers}; valid cells in Maharashtra box on day 1: {valid_cells}; "
          f"checked year {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}; all 18 file sizes exact; "
          f"units attr: {v.attrs.get('units')}")
    assert covers, f"{var} grid does not cover Maharashtra"
    days = sum(366 if leap(y) else 365 for y in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1))
    return {"var": var, "step": grid.step, "nlon": grid.nlon, "nlat": grid.nlat, "extent": ext, "covers": covers,
            "valid_cells_box": valid_cells, "units_attr": v.attrs.get("units"), "days": days}


def write_sources_doc(brows, grid_info, mh_n, bounds) -> None:
    man = json.loads((C.IMD_CACHE_DIR / "manifest.json").read_text())["files"]
    lines = [
        "# Data sources (raw files)", "",
        f"Generated by src/05a_download_weather.py on {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
        "Raw files are never edited. Sizes in bytes; sha256 for integrity.", "",
        "## IMD gridded daily data (via imdlib)", "",
        f"Downloaded with imdlib {imdlib.__version__} (`imdlib.load`, archive source; MIT licence; "
        "Nandi, Patel and Swain 2024, doi:10.1016/j.envsoft.2023.105869). Each yearly file is an HTTP POST to the "
        "URL below with the form field shown. Rainfall: Pai et al. (2014), MAUSAM 65(1), 1-18. "
        "Data provider: India Meteorological Department, Pune. Binary little-endian float32, (day, lat, lon).", "",
    ]
    for g in grid_info:
        var = g["var"]
        lines += [f"### {var}: {PRODUCT[var]}", "",
                  f"- URL: {ARCHIVE_URLS[var][0]} (POST field `{ARCHIVE_URLS[var][1]}` = year)",
                  f"- Units: {UNITS[var]} (missing value {'-999' if var == 'rain' else '99.9'}); xarray units attribute: "
                  f"{g['units_attr']}",
                  f"- Grid: {g['step']} deg, {g['nlon']} x {g['nlat']} cells; extent lon {g['extent'][0]:.3f} to "
                  f"{g['extent'][2]:.3f} E, lat {g['extent'][1]:.3f} to {g['extent'][3]:.3f} N; covers Maharashtra: "
                  f"{g['covers']}; {g['days']} days", "",
                  "| file | POST data | retrieved (UTC) | size | sha256 |", "|---|---|---|---|---|"]
        for y in range(C.WEATHER_YEAR_START, C.WEATHER_YEAR_END + 1):
            rec = man[f"archive/{var}/{y}.grd"]
            path = C.IMD_CACHE_DIR / "archive" / var / f"{y}.grd"
            assert path.stat().st_size == rec["size"], f"size mismatch {path}"
            lines.append(f"| {path.relative_to(C.ROOT)} | {rec['post_data']} | {rec['downloaded']} | "
                         f"{rec['size']:,} | `{rec['sha256'][:16]}...` |")
        lines.append("")
    lines += ["## District boundaries: 2011 Census districts (DataMeet maps)", "",
              f"- Repository: https://github.com/{C.DATAMEET_REPO}, layer `{C.DATAMEET_LAYER}` (shapefile), pinned to "
              f"commit {C.DATAMEET_COMMIT}",
              f"- Licence: {C.DATAMEET_LICENCE}",
              "- Provenance (Districts/README.md): taluk boundaries from GeoCommons and Bhuvan; names and extent from "
              "the Census of India 2011 Administrative Atlas.",
              f"- Maharashtra: {mh_n} districts; bounds lon {bounds[0]:.3f} to {bounds[2]:.3f} E, lat {bounds[1]:.3f} "
              f"to {bounds[3]:.3f} N", "",
              "| file | URL | retrieved (UTC) | size | sha256 |", "|---|---|---|---|---|"]
    for r in brows:
        lines.append(f"| {r['file']} | {r['url']} | {r['retrieved_utc']} | {r['size']:,} | `{r['sha256'][:16]}...` |")
    lines += ["", "## Files supplied by the user (unchanged, see docs/notes.md)", "",
              "- data/raw/ICRISAT-District_Level_Data.csv, data/raw/rainfall_in_india_1901-2015.csv, "
              "data/raw/district_wise_rainfall_normal.csv (normal period not stated in the file), "
              "data/raw/era5_point_temperature.csv (rejected).", ""]
    C.DATA_SOURCES_DOC.write_text("\n".join(lines))
    print(f"Wrote {C.DATA_SOURCES_DOC.relative_to(C.ROOT)}")


def main() -> None:
    print("1. Boundaries (DataMeet 2011 Census districts)")
    brows = download_boundaries()
    bounds, mh_n = maharashtra_bounds()
    print(f"  Maharashtra: {mh_n} districts; bounds {np.round(bounds, 3)}")
    print("2. IMD grids via imdlib")
    data = download_imd()
    grid_info = [check_grid(v, data[v], bounds) for v in C.IMD_VARS]
    write_sources_doc(brows, grid_info, mh_n, bounds)


if __name__ == "__main__":
    main()
