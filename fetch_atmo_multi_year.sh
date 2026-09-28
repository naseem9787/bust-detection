#!/usr/bin/env bash
# Phase 3 atmospheric variable fetch - split by cost (see
# src/phase3/atmospheric_features.py's module docstring for why):
#   - 10m_wind_speed: cheap, fetched year-by-year at full JJAS 2018-2021 scale
#   - specific_humidity (850hPa) + geopotential (500hPa): ~13x more
#     expensive per unit of coverage (chunk bundles all 13 pressure levels),
#     so fetched ONLY for the same bounded pilot window as the ensemble data
set -e
START_YEAR="${1:?usage: fetch_atmo_multi_year.sh START_YEAR END_YEAR}"
END_YEAR="${2:?usage: fetch_atmo_multi_year.sh START_YEAR END_YEAR}"

for Y in $(seq "$START_YEAR" "$END_YEAR"); do
  echo "=========== WIND YEAR $Y (cheap, full scale) ==========="
  ./.venv/Scripts/python.exe -u -m src.phase3.atmospheric_features wind --start "${Y}-01-01" --end "${Y}-12-31"
done

echo "=========== LEVELS (humidity + geopotential, pilot scope) ==========="
./.venv/Scripts/python.exe -u -m src.phase3.atmospheric_features levels --start 2021-07-15 --end 2021-08-04

echo "ALL ATMO FETCHES DONE"
