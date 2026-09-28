#!/usr/bin/env bash
# Fetch several full calendar years one at a time, then rebuild the error
# database / bust labels / summary once at the end.
#
# Fetching year-by-year (instead of one continuous multi-year range) means a
# transient network blip only costs the year in progress - already-downloaded
# years stay cached and are skipped on retry (see fetch_data.py's cache check
# via run_phase0.py, or just re-run this script; each year's .nc files are
# only written after a full successful download).
#
# Usage:
#   ./fetch_multi_year.sh 2018 2021
set -e

START_YEAR="${1:?usage: fetch_multi_year.sh START_YEAR END_YEAR}"
END_YEAR="${2:?usage: fetch_multi_year.sh START_YEAR END_YEAR}"

for Y in $(seq "$START_YEAR" "$END_YEAR"); do
  echo "=========== YEAR $Y ==========="
  ./.venv/Scripts/python.exe -u -m src.fetch_data --start "${Y}-01-01" --end "${Y}-12-31"
done

echo "=========== BUILD ERROR DB ==========="
./.venv/Scripts/python.exe -u -m src.build_error_db
echo "=========== LABEL BUSTS ==========="
./.venv/Scripts/python.exe -u -m src.label_busts
echo "=========== SUMMARIZE ==========="
./.venv/Scripts/python.exe -u -m src.summarize
echo "ALL DONE"
