# Data dictionary: data/processed/panel_v1.csv

Written 2026-10-18. PROTOTYPE panel (13 columns since 2026-10-18): 208 rows = 13 districts x 16 years (2000-2015), one row per district-year. Built by src/01_clean_icrisat.py and src/02_build_panel_subdivision.py.

ICRISAT = data/raw/ICRISAT-District_Level_Data.csv (district-level, older district boundaries).
IMD = data/raw/rainfall_in_india_1901-2015.csv (monthly rainfall by meteorological subdivision).

| Column | Unit | Source | Definition |
|---|---|---|---|
| district | - | ICRISAT `Dist Name` | District name as spelled in ICRISAT (e.g. "Amarawati", "Yeotmal"). Panel entity. |
| dist_code | - | ICRISAT `Dist Code` | ICRISAT numeric district code. |
| subdivision | - | data/interim/district_subdivision_map.csv | IMD meteorological subdivision containing the district, spelled as in IMD ("VIDARBHA", "MATATHWADA" = Marathwada, "MADHYA MAHARASHTRA"). |
| year | calendar year | ICRISAT `Year` | Crop year as recorded by ICRISAT; matched to the same calendar year's Jun-Sep monsoon. |
| trend | years | derived | year - 2000 (config.TREND_BASE_YEAR). 0 = 2000. |
| area_kha | thousand ha | ICRISAT `SOYABEAN AREA (1000 ha)` | Soybean area harvested. Always > 0 here (zero area = not grown, dropped). |
| prod_kt | thousand tonnes | ICRISAT `SOYABEAN PRODUCTION (1000 tons)` | Soybean production. |
| yield_kgha | kg/ha | ICRISAT `SOYABEAN YIELD (Kg per ha)` | Reported soybean yield; equals 1000 * prod_kt / area_kha to within 0.1 kg/ha. Robustness outcome. |
| ln_yield | ln(kg/ha) | derived | Natural log of yield_kgha. Main outcome. |
| R_season | mm | IMD `JUN`+`JUL`+`AUG`+`SEP` | Jun-Sep (monsoon) rainfall total for the district's subdivision. Identical for all districts in a subdivision. |
| R_early | mm | IMD `JUN`+`JUL` | Jun-Jul rainfall total for the subdivision (sowing/establishment). |
| R_late | mm | IMD `AUG`+`SEP` | Aug-Sep rainfall total for the subdivision (flowering/pod filling). |
| R_julsep | mm | IMD `JUL`+`AUG`+`SEP` | Jul-Sep rainfall total for the subdivision. Added 2026-10-18 for the alternative-window robustness check (src/09). |

Notes
- Rainfall columns are subdivision-level, not district-level: only 3 distinct series appear in the panel.
- No temperature columns. panel_final.csv (src/05) will keep these exact column names and units and add T_season, T_early, T_late (deg C).
- data/processed/panel_v1_wide.csv has the same columns for the wider robustness district set (13 + Aurangabad, Ahmednagar, Nasik, Satara): 272 rows = 17 x 16 (SPEC amendment A5).
- Squared rainfall terms (`*_sq`) are created inside src/04 and are not stored in the panel.
