# Phase 3 Variable Inventory

New atmospheric variables added on top of Phase 0-2's (total_precipitation_24hr, 2m_temperature, mean_sea_level_pressure), fetched via src/phase3/atmospheric_features.py at FULL JJAS 2018-2021 scale (deterministic HRES/ERA5 stores - no ensemble dimension, so full-scale fetch is affordable, unlike the ensemble pilot).

| Variable | Priority | Source | Units | Pressure level | Spatial res. | Temporal res. | Transformation |
|---|---|---|---|---|---|---|---|
| `10m_wind_speed` | 1 - wind | 10m_wind_speed (both HRES forecast and ERA5 truth stores - already a derived magnitude in WeatherBench2, not computed here from u/v) | m/s | surface (10m) - no pressure level | 1.5 degree (240x121 grid) - same grid as all Phase 0-2 variables, no regridding | 6-hourly lead steps, same init cadence (00Z/12Z) as HRES | none - used as-is |
| `specific_humidity` | 2 - humidity/moisture | specific_humidity @ 850hPa (classic low-level monsoon moisture-flux level) | g/kg (converted from kg/kg by x1000 for readability, matching the project's existing unit-conversion convention) | 850 hPa | 1.5 degree (240x121 grid) | 6-hourly lead steps | kg/kg -> g/kg (x1000) |
| `geopotential` | 3 - geopotential | geopotential @ 500hPa (classic synoptic-scale pattern / trough-ridge indicator) | m (geopotential height, converted from geopotential in m^2/s^2 by dividing by standard gravity 9.80665) | 500 hPa | 1.5 degree (240x121 grid) | 6-hourly lead steps | geopotential (m^2/s^2) / 9.80665 -> geopotential height (m) |

## Deliberately not added this pass

- u/v wind components at pressure levels (kept only the surface wind-speed magnitude, to avoid an explosion of near-duplicate directional features for a first pass)
- temperature/humidity/wind at OTHER pressure levels (only one representative level per variable was kept - 850hPa for moisture, 500hPa for geopotential - per the instruction to keep the feature set meteorologically interpretable, not exhaustive)
- vertical velocity, relative humidity, total cloud cover - available in the source stores but not prioritized for this pass (wind/humidity/geopotential were the explicit priorities)

## Truth (ERA5) equivalents

Also fetched (data/raw/atmo_truth_*.nc) for potential future use (e.g. defining a wind- or moisture-based bust target), but NOT used as a model input anywhere in Phase 3 - only the FORECAST values feed the feature table, per the leakage rules (see outputs/phase3/feature_registry.csv).