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
