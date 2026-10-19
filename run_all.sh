#!/usr/bin/env bash
# Run the whole pipeline from data/raw, in order (SPEC A14.6). From the repo root:
#   bash run_all.sh                  # downloads (05a) are re-checked; cached files are reused
#   bash run_all.sh --skip-download  # skip 05a; fails if the IMD grids or boundaries are missing
#   bash run_all.sh --prototype      # also re-run the historical prototype steps (03 and 04 on panel_v1)
# Uses .venv/bin/python. Stops at the first error.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
export MPLCONFIGDIR="${MPLCONFIGDIR:-$(mktemp -d)}"
SKIP_DOWNLOAD=0
PROTOTYPE=0
for arg in "$@"; do
  case "$arg" in
    --skip-download) SKIP_DOWNLOAD=1 ;;
    --prototype) PROTOTYPE=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done
FINAL=data/processed/panel_final.csv
WIDE=data/processed/panel_final_wide.csv
step() { echo; echo "=== $* ==="; "$@"; }

step $PY src/01_clean_icrisat.py
step $PY src/02_build_panel_subdivision.py
if [ "$PROTOTYPE" = 1 ]; then
  step $PY src/03_eda.py data/processed/panel_v1.csv outputs/prototype
  step $PY src/04_models_prototype.py
fi
if [ "$SKIP_DOWNLOAD" = 1 ]; then
  n=$(ls data/raw/grids/imd/archive/{rain,tmax,tmin}/*.grd 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" != 54 ] || [ ! -f data/raw/boundaries/datameet_census2011/2011_Dist.shp ]; then
    echo "--skip-download: expected 54 IMD .grd files and the DataMeet layer, found $n grids" >&2; exit 1
  fi
  echo; echo "=== 05a skipped (--skip-download; 54 grids and boundaries present) ==="
else
  step $PY src/05a_download_weather.py
fi
step $PY src/05_build_panel_gridded.py
step $PY src/05c_diagnose_ghats.py
step $PY src/05b_validate_panel.py
step $PY src/03_eda.py "$FINAL" outputs/final
step $PY src/06_models_final.py "$FINAL" outputs/final
step $PY src/07_diagnostics.py "$FINAL" outputs/final
step $PY src/08_scenario_100mm.py "$FINAL" outputs/final
step $PY src/09_robustness.py "$FINAL" outputs/final --wide-panel "$WIDE"
step $PY src/11_sanity_checks.py "$FINAL" outputs/final
step $PY src/10_results_summary.py
step $PY src/12_report_inputs.py
step $PY src/13_collect_report_figures.py
echo; echo "run_all.sh: all steps completed"