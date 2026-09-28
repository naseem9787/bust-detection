# Phase 2 Feature Availability

| Feature | Category | Available now | Description |
|---|---|---|---|
| `fcst_precip_mm` | forecast state | YES | HRES forecast 24h precip, this row's lead day |
| `fcst_temp_c` | forecast state | YES | HRES forecast 2m temperature |
| `fcst_mslp_hpa` | forecast state | YES | HRES forecast mean sea level pressure |
| `latitude` | spatial | YES | grid cell latitude |
| `longitude` | spatial | YES | grid cell longitude |
| `region_v2` | spatial | YES | Phase-2 full-coverage state/UT region (src/phase2/geography.py) |
| `fcst_precip_anomaly_vs_domain_mean` | spatial structure | YES | this cell's forecast minus the domain-wide mean forecast at the same (init_time, lead_day) - a cheap, vectorized proxy for 'how unusual is this forecast relative to the broader pattern that day', computed from forecast data alone (no truth involved) |
| `fcst_temp_anomaly_vs_domain_mean` | spatial structure | YES | same, for temperature |
| `lead_day` | temporal | YES | forecast lead day (1-10) |
| `month` | temporal | YES | calendar month of the valid date (6-9, JJAS) |
| `precip_forecast_jump` | temporal - forecast evolution | YES | this forecast's precip minus the PREVIOUS day's forecast run for the SAME valid_time/grid-cell (i.e. lead_day+1 issued 24h earlier) - 'did the model change its mind since yesterday's run', standard operational run-to-run consistency signal. Only defined for lead_day 1-9 and where the earlier run exists in the JJAS window. |
| `temp_forecast_jump` | temporal - forecast evolution | YES | same, for temperature |
| `hist_bust_rate_region_lead_month` | historical behaviour | YES | train-only-fit climatological rate of the TARGET label for this (region, lead_day, month) - i.e. Phase 1's Baseline A, fed in as a feature rather than used only as a standalone baseline |
| `hist_mean_abs_error_region_lead_month` | historical behaviour | YES | train-only-fit mean |forecast error| for this (region, lead_day, month), for the same variable the target is defined on |
| `ensemble_mean / ensemble_std / ensemble_spread` | ensemble | NO | SEE MODULE DOCSTRING |
| `wind, humidity, geopotential height` | forecast state (not fetched) | NO | confirmed available in the source HRES zarr store (verified variable listing during Phase 0) but not downloaded into data/raw/ this pass - adding them means re-running fetch_data.py-style downloads for JJAS 2018-2021, deferred to keep this pass modest per instructions |

## Ensemble data availability check

See this module's docstring for the full account. Summary: the `ifs_ens` dataset exists in the WeatherBench2 bucket (chunk data confirmed present) but its zarr metadata could not be read via direct HTTP or `xarray.open_zarr` in the time available - the same 'missing .zgroup' failure mode Phase 0 hit and worked around for ERA5 by using a different, well-formed store; no equivalent well-formed ensemble store was found tonight. Not fabricated - documented as unavailable, matching Phase 1's Baseline C.

## Deferred (not fabricated, not modeled this pass)

- Ensemble mean/std/spread/quantiles - blocked, see above.
- Wind, humidity, geopotential height - available in the source store but not yet downloaded; would require extending `src/config.py VARIABLES` and re-running the Phase-0 fetch for JJAS 2018-2021, out of scope for tonight's modest first model.
- Full neighbor-adjacency spatial gradients (as opposed to the cheap domain-mean-anomaly proxy actually used) - a reasonable next enhancement, not built tonight to keep scope modest.