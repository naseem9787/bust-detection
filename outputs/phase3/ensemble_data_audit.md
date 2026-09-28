# Phase 3 Ensemble Data Audit

## Investigation history

### Phase 2 attempt (failed)
Tried `gs://weatherbench2/datasets/ifs_ens/2016-2024-240x121_equiangular_with_poles_conservative.zarr`
(the store name that appeared first in a plain bucket listing). Chunk *data*
objects exist under it, but:
- `.zgroup` / `.zmetadata` / per-variable `.zarray` all return `404 NoSuchKey`
  via direct HTTP.
- `xarray.open_zarr(...)` raises `GroupNotFoundError`.

This is the same failure mode Phase 0 hit for one ERA5 store and worked
around by switching to a different, properly-formed store. Time-boxed in
Phase 2, documented as unavailable, not resolved then.

### Phase 3 attempt (succeeded)
Re-investigated per Phase 3 instructions (Stage A: "try reasonable, bounded
approaches" before giving up). Listed ALL `ifs_ens` store variants in the
bucket (`gsutil`-equivalent listing via the public JSON API) rather than
assuming the first name found was the only option:

```
datasets/ifs_ens/2016-2024-1440x721.zarr/                                              (not checked - full-res, too large)
datasets/ifs_ens/2016-2024-240x121_equiangular_with_poles_conservative.zarr/           BROKEN (404 on .zgroup)
datasets/ifs_ens/2016-2024-240x121_equiangular_with_poles_conservative_mean.zarr/      BROKEN (404 on .zgroup)
datasets/ifs_ens/2016-2024-64x32_equiangular_conservative.zarr/                        (not checked)
datasets/ifs_ens/2016-2024-64x32_equiangular_conservative_mean.zarr/                   (not checked)
datasets/ifs_ens/2018-2022-1440x721.zarr/                                              (not checked - full-res, too large)
datasets/ifs_ens/2018-2022-1440x721_mean.zarr/                                         (not checked)
datasets/ifs_ens/2018-2022-240x121_equiangular_with_poles_conservative.zarr/           WORKS
datasets/ifs_ens/2018-2022-240x121_equiangular_with_poles_conservative_mean.zarr/      WORKS (not needed - full ensemble works)
datasets/ifs_ens/2018-2022-64x32_equiangular_conservative.zarr/                        WORKS (not needed - too coarse)
```

**Working store:** `gs://weatherbench2/datasets/ifs_ens/2018-2022-240x121_equiangular_with_poles_conservative.zarr`
(a differently-versioned write of the same underlying product - "2018-2022"
date-range naming, not "2016-2024" - with correct `.zgroup`/`.zmetadata`).
Opened successfully with `xarray.open_zarr(..., consolidated=True)` in 5.6s.

## Structure (confirmed by opening the store)

| Property | Value |
|---|---|
| Source | ECMWF IFS ensemble forecast (`ifs_ens`) |
| Time (init) coverage | 2018-01-01 to 2022-12-31, 00Z/12Z (same cadence as the deterministic HRES store already in use) |
| Ensemble members | 50 (`number` dim, values 1-50) |
| Lead time | 0-360h every 6h (61 steps) - LONGER than HRES's 0-240h (41 steps) |
| Grid | 240 x 121 (1.5-degree), longitude 0-358.5, latitude -90 to 90 - **identical grid to the deterministic HRES/ERA5 stores already used in Phase 0-2**, no regridding needed |
| Pressure levels | 500, 700, 850 hPa |
| Variables | 10m_u/v_component_of_wind, 10m_wind_speed, 2m_temperature, geopotential, mean_sea_level_pressure, relative_humidity, specific_humidity, temperature, total_precipitation(/_6hr/_24hr), u/v_component_of_wind, wind_speed |
| Units | 2m_temperature in K (same as HRES); total_precipitation_24hr has no `units` attribute recorded in this store but is presumed meters (same ECMWF/WB2 convention as HRES/ERA5 - both HRES and ERA5 stores in Phase 0 also convert from meters) |

## The volume problem, and the scope decision

Chunk shape for a surface variable is `(1, 50, 8, 240, 121)` - i.e. ONE init
time, ALL 50 members, 8 consecutive lead steps, the FULL spatial grid. As
established in Phase 0 (the same lesson applies here), zarr always fetches
whole chunks over the network even when only a spatial subset is wanted, so
the ensemble dimension multiplies download volume ~50x relative to the
deterministic HRES store for the same date/lead/variable coverage - roughly
46.5MB per chunk vs. ~0.93MB for the equivalent HRES chunk.

Extrapolating from the Phase 0 HRES full-year fetch's observed throughput
(~12.2GB in ~1000s, ~12.2MB/s effective), a full JJAS-2018-2021-scale
ensemble fetch (976 forecast issuances x ~6 chunks x N variables x 46.5MB)
would run into the **hundreds of GB and many hours** even for just 2
variables - not a "bounded, reasonable" download for a single overnight run
that also has to cover Stages C-O.

**Decision (per Stage P's computational-discipline rules and Stage B's own
"extract only what's required" instruction):** fetch a deliberately small,
clearly-scoped PILOT rather than the full 4-season window:

- **Window:** 2021-07-15 to 2021-08-04 (21 days x 2 inits/day = 42 forecast
  issuances) - inside the 2021 TEST year, so the pilot can be evaluated
  against the same held-out season the rest of Phase 2/3 uses.
- **Variables:** `total_precipitation_24hr`, `2m_temperature` only - the two
  variables that directly match the two candidate targets.
- **Immediately reduced to statistics** (mean, std, min, max, p25, p75)
  across the 50-member axis right after loading - raw per-member values are
  never persisted to disk, only the aggregated stats, per Stage B/P.
- Estimated volume: 42 inits x ~6 chunks x 2 vars x 46.5MB =~ 23GB network
  transfer, ~30-35 minutes at the observed throughput - a bounded,
  documented, one-time cost.

This is a genuine, non-fabricated ensemble dataset - just deliberately
small in date-range scope. Every downstream ensemble-feature analysis in
Phase 3 (ablation Model 7, event analysis where applicable) is run ONLY
over this pilot window and is explicitly labeled as such - it is NOT
presented as covering the full 2021 test set the rest of Phase 3 uses.

## What this means for Stage F (ablation)

Model 7 ("+ ensemble") in the ablation study is evaluated on the pilot
window's test-period overlap only (a few hundred to a few thousand rows,
not the full ~446,520-row 2021 test set) - see
`outputs/phase3/ablation_results.csv`'s row count column and the caveat in
the final report. This is an honest constraint of the available compute
budget, not a data-quality problem with the ensemble store itself.
