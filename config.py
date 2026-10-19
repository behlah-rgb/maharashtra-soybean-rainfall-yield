"""Project configuration: paths, seed, year range, thresholds, file names.

All scripts in src/ import from here. Nothing in src/ hard-codes these values.
"""
from pathlib import Path

# ---- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
GRIDS_DIR = DATA_RAW / "grids"
OUT_FIGURES = ROOT / "outputs" / "figures"
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_LOGS = ROOT / "outputs" / "logs"

# ---- Raw input files (never edited) -----------------------------------------
ICRISAT_FILE = DATA_RAW / "ICRISAT-District_Level_Data.csv"
IMD_SUBDIV_FILE = DATA_RAW / "rainfall_in_india_1901-2015.csv"
DISTRICT_NORMAL_FILE = DATA_RAW / "district_wise_rainfall_normal.csv"  # not used in regression
ERA5_POINT_FILE = DATA_RAW / "era5_point_temperature.csv"              # rejected, not used in model

# ---- Interim / processed files ----------------------------------------------
DISTRICT_MAP_FILE = DATA_INTERIM / "district_subdivision_map.csv"
SOY_CLEAN_FILE = DATA_PROCESSED / "soy_clean.csv"
PANEL_V1_FILE = DATA_PROCESSED / "panel_v1.csv"
PANEL_FINAL_FILE = DATA_PROCESSED / "panel_final.csv"
ICRISAT_AUDIT_FILE = OUT_TABLES / "icrisat_audit.csv"
PROTOTYPE_LOG_FILE = OUT_LOGS / "prototype_models.txt"

# ---- Study design ------------------------------------------------------------
STATE_NAME = "Maharashtra"
CROP = "SOYABEAN"                 # spelling used in ICRISAT headers
YEAR_START = 2000                 # first year of the target period
YEAR_END_TARGET = 2017            # last year of the target period (ICRISAT ends here)
YEAR_END_FALLBACK = 2015          # IMD subdivision rainfall ends in 2015
TREND_BASE_YEAR = 2000            # trend t = year - TREND_BASE_YEAR

# District selection rule: at least MIN_YEARS years with area >= AREA_THRESHOLD,
# counted over YEAR_START..YEAR_END_TARGET.
AREA_THRESHOLD = 20.0             # thousand ha
MIN_YEARS = 15

# Districts the user expects the rule to produce (used only to report differences).
EXPECTED_DISTRICTS = [
    "Akola", "Amarawati", "Beed", "Buldhana", "Chandrapur", "Kolhapur", "Nagpur",
    "Nanded", "Osmanabad", "Parbhani", "Sangli", "Wardha", "Yeotmal",
]

# Months (IMD column names) for the rainfall windows.
MONTHS_SEASON = ["JUN", "JUL", "AUG", "SEP"]
MONTHS_EARLY = ["JUN", "JUL"]
MONTHS_LATE = ["AUG", "SEP"]

# ---- Yield consistency check -------------------------------------------------
YIELD_CHECK_TOL = 1.0             # kg/ha; max allowed |reported - 1000*prod/area|

# ---- EDA ---------------------------------------------------------------------
OUTLIER_SD = 3.0                  # flag district-years > OUTLIER_SD from district mean

# ---- Experiment and inference ------------------------------------------------
RAIN_SHOCK_MM = 100.0             # rainfall deficit for the experiment
SEED = 28                         # Group 28
N_BOOT = 1000

PROTOTYPE_HEADER = ("PROTOTYPE - NOT FOR THE REPORT: rainfall is subdivision-level "
                    "and has no temperature.")

# ---- District -> IMD subdivision map (written to DISTRICT_MAP_FILE by src/01) --
# Subdivision strings are spelled exactly as in the IMD file ("MATATHWADA" sic).
DISTRICT_SUBDIVISION = {
    "VIDARBHA": ["Akola", "Amarawati", "Buldhana", "Yeotmal", "Wardha", "Nagpur",
                 "Chandrapur", "Bhandara"],
    "MATATHWADA": ["Aurangabad", "Beed", "Nanded", "Osmanabad", "Parbhani"],
    "MADHYA MAHARASHTRA": ["Ahmednagar", "Dhule", "Jalgaon", "Kolhapur", "Nasik", "Pune",
                           "Sangli", "Satara", "Solapur"],
    "KONKAN & GOA": ["Bombay", "Raigad", "Ratnagiri", "Thane"],
}

# ---- Amendments 2026-10-18 (see docs/SPEC.md) -----------------------------------
# Output roots for src/06-09. Scripts refuse to write under OUT_FINAL unless the input
# panel is PANEL_FINAL_FILE (or PANEL_FINAL_WIDE_FILE for the wider district set).
OUT_PROTOTYPE = ROOT / "outputs" / "prototype"
OUT_FINAL = ROOT / "outputs" / "final"
FINAL_HEADER = "FINAL: district-level gridded panel (panel_final.csv)."

# Wider district set for robustness (A5): the 13 districts plus these four.
ROBUST_EXTRA_DISTRICTS = ["Aurangabad", "Ahmednagar", "Nasik", "Satara"]
SOY_CLEAN_WIDE_FILE = DATA_PROCESSED / "soy_clean_wide.csv"
PANEL_V1_WIDE_FILE = DATA_PROCESSED / "panel_v1_wide.csv"
PANEL_FINAL_WIDE_FILE = DATA_PROCESSED / "panel_final_wide.csv"

# Alternative rainfall window for robustness: Jul-Sep.
MONTHS_JULSEP = ["JUL", "AUG", "SEP"]

# Robustness: drop each of these drought years in turn (team-lead list).
DROUGHT_YEARS = [2009, 2014, 2015]

# Illustrative weak-monsoon scenarios: rainfall at these fractions of each district's mean.
WEAK_MONSOON_FRACTIONS = [0.9, 0.8]

# Number of grid points for the 100 mm effect across the observed rainfall range.
RANGE_GRID_POINTS = 50

# ---- Amendments 2026-10-19 (A7-A10, see docs/SPEC.md) ------------------------------
# A7 inference
BLOCK_LENGTH = 3                      # moving-block bootstrap over years (headline)
BLOCK_LENGTH_SENSITIVITY = [2, 4]
N_BOOT_BLOCK = 2000
BOOT_SEEDS = {                        # one seed per resampling scheme; same draws in src/06 and src/08
    "block_L2": 2802,
    "block_L3": 2803,
    "block_L4": 2804,
    "districts": 2810,
    "wild": 2820,                     # used only if the wild bootstrap cannot enumerate all sign vectors
}
DK_MAXLAGS = 2                        # Driscoll-Kraay Bartlett kernel, lags 0..2
WILD_ENUMERATE_MAX_CLUSTERS = 14      # enumerate all 2^G Rademacher vectors when G <= this
N_WILD = 9999                         # random wild draws otherwise
ALPHA = 0.05

# A10 robustness: selected districts whose old boundaries include a later split.
BOUNDARY_SENSITIVE_DISTRICTS = ["Akola", "Parbhani", "Osmanabad", "Chandrapur"]

# A10/A11 old-to-new district crosswalk: (current district, ICRISAT district, status, note).
# Statuses: CONFIRMED_OFFICIAL_PAGE, CAVEAT, ALIAS_NAME_ONLY (rename, same boundary; A11), UNVERIFIED.
# A current district whose name equals an ICRISAT district maps to itself and needs no row. src/05
# refuses to write panel_final.csv only if a row it uses is UNVERIFIED (ALIAS_NAME_ONLY never blocks).
_SRC = ("Maharashtra government district-history page cited in the teammate's report; "
        "not independently verified")
DISTRICT_CROSSWALK = [
    ("Latur", "Osmanabad", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Gadchiroli", "Chandrapur", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Nandurbar", "Dhule", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Hingoli", "Parbhani", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Gondia", "Bhandara", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Jalna", "Aurangabad", "CONFIRMED_OFFICIAL_PAGE",
     _SRC + ". CAVEAT kept (A11): Jalna also took Partur taluka from Parbhani; Jalna is kept wholly in "
     "Aurangabad, so old Parbhani loses Partur (limitation, no taluka-level handling)"),
    ("Palghar", "Thane", "CONFIRMED_OFFICIAL_PAGE", _SRC),
    ("Washim", "Akola", "CONFIRMED_OFFICIAL_PAGE",
     "verified by the team lead (2026-10-19) from two official sources: Central Ground Water Board Washim "
     "district document; Akola district website history page (Washim carved from Akola on 1 July 1998). "
     "The Yavatmal mention in the teammate's report is the 1905 history; no adjustment to old Yeotmal (A13.1)"),
    # A11: renames, same boundaries.
    ("Dharashiv", "Osmanabad", "ALIAS_NAME_ONLY", "rename of Osmanabad; same boundary (A11)"),
    ("Chhatrapati Sambhajinagar", "Aurangabad", "ALIAS_NAME_ONLY", "rename of Aurangabad; same boundary (A11)"),
    ("Ahilyanagar", "Ahmednagar", "ALIAS_NAME_ONLY", "rename of Ahmednagar; same boundary (A11)"),
    # Not covered by the team lead: UNVERIFIED until confirmed (not used by the 13- or 17-district panels).
    ("Mumbai Suburban", "Bombay", "UNVERIFIED", "candidate pair"),
    ("Mumbai City", "Bombay", "UNVERIFIED", "candidate pair"),
    ("Sindhudurg", "Ratnagiri", "UNVERIFIED",
     "carved from Ratnagiri in 1981; not on the team lead's list; mapping approved by the user 2026-10-19 "
     "as UNVERIFIED; Konkan only, used in no panel"),
]

# ---- A12 (2026-10-19): weather data acquired via imdlib; DataMeet 2011 boundaries ----------
IMD_CACHE_DIR = GRIDS_DIR / "imd"            # imdlib cache layout: archive/<var>/<year>.grd
IMD_VARS = ["rain", "tmax", "tmin"]
WEATHER_YEAR_START, WEATHER_YEAR_END = 2000, 2017
DOWNLOAD_MAX_ATTEMPTS = 2                    # imdlib.load calls per variable (each retries internally)

BOUNDARY_DIR = DATA_RAW / "boundaries" / "datameet_census2011"
DATAMEET_REPO = "datameet/maps"
DATAMEET_COMMIT = "b3fbbde595310b397a55d718e0958ce249a4fa1f"   # master HEAD on 2026-10-19
DATAMEET_LAYER = "Districts/Census_2011/2011_Dist"
DATAMEET_EXTS = [".shp", ".shx", ".dbf", ".prj"]
DATAMEET_LICENCE = ("CC BY 2.5 India (Districts/README.md); repository data default CC BY 4.0; code MIT. "
                    "Attribution: DataMeet India community")
STATE_NAME_BOUNDARY = "Maharashtra"
EXPECTED_N_CURRENT_DISTRICTS = 35            # 2011 Census, matches district_wise_rainfall_normal.csv
EQUAL_AREA_CRS = "ESRI:102028"               # Asia South Albers Equal Area Conic

DATA_SOURCES_DOC = ROOT / "docs" / "data_sources.md"
OLD_TO_CURRENT_FILE = DATA_INTERIM / "old_to_current_districts.csv"
OLD_DISTRICTS_GPKG = DATA_INTERIM / "old_districts.gpkg"
OLD_DISTRICT_WEATHER_FILE = DATA_INTERIM / "old_district_weather.csv"
CELL_WEIGHTS_FILE = DATA_INTERIM / "grid_cell_weights.csv"
CROSSWALK_SOURCE_NOTE = ("source: Maharashtra government district-history pages via teammate report, "
                         "not independently verified")

# Approved spelling variants, A12.3: boundary-layer or normals-file spelling -> canonical name, which is
# either an ICRISAT district (identity) or the current-district name used in DISTRICT_CROSSWALK.
# First four: team lead (A12). Next six: approved by the user on 2026-10-19 after the DataMeet layer was
# inspected (Census 2011 spellings, codes 523, 500, 520, 508, 507, 519). "Mumbai Sub": normals-file
# abbreviation (my addition, flagged; affects only Bombay, which is in no panel).
SPELLING_VARIANTS = {"Amravati": "Amarawati", "Yavatmal": "Yeotmal", "Nashik": "Nasik",
                     "Ahmadnagar": "Ahmednagar",
                     "Bid": "Beed", "Buldana": "Buldhana", "Raigarh": "Raigad",
                     "Garhchiroli": "Gadchiroli", "Gondiya": "Gondia", "Mumbai": "Mumbai City",
                     "Mumbai Sub": "Mumbai Suburban"}

SEASON_START_MMDD, SEASON_END_MMDD = "06-01", "09-30"
EARLY_END_MMDD = "07-31"                     # R_early = Jun-Jul; R_late = Aug-Sep; R_julsep = Jul-Sep
DRY_DAY_MM = 2.5
VALIDATION_NORMAL_TOL = 0.25                 # flag old districts off the normals by more than 25%

# ---- A13 (2026-10-19) -------------------------------------------------------------------------
# Per-row override of the crosswalk "source" column (all other rows: CROSSWALK_SOURCE_NOTE).
CROSSWALK_SOURCE_OVERRIDES = {
    "Washim": ("source: team lead, from the Central Ground Water Board Washim document and the Akola district "
               "website (Washim carved from Akola on 1 July 1998)"),
}
DQ_ROBUST_Z = 3.0                 # dq_flag screen: |R_season - district median| > 3 x 1.4826 x MAD
DQ_EXTRA_CASES = [("Ratnagiri", 2008), ("Raigad", 2008), ("Pune", 2005)]
DQ_DAILY_CELL_MM = 300.0          # diagnostic: cell-days above this daily rainfall
RAIN_UNIT_MM = 100.0              # Rc = (R_season - grand mean) / RAIN_UNIT_MM
EXCLUDE_GHATS_DISTRICTS = ["Kolhapur", "Sangli"]
EARLY_YEARS_DROP = [2000, 2001, 2002, 2003]
DQ_FLAGS_FILE = DATA_INTERIM / "dq_flags.csv"
