# Historical Analog Intelligence (Phase 5)

**Framing (repeat everywhere):** "The system retrieves historical forecast
situations that were similar to the current forecast and reports their
realized outcomes." This is evidence, not proof — similarity does not
guarantee a similar outcome, and nothing here claims a causal relationship.

## 1. Analog definition

A historical analog is a past (init_time, lead_day, grid cell) forecast
record whose **forecast-only feature vector** is close (standardized
Euclidean distance) to the current forecast's vector, subject to spatial
and temporal constraints, with future-relative-to-query records excluded.

## 2. Feature vector

`fcst_precip_mm, fcst_temp_c, fcst_mslp_hpa, wind_speed_10m,
precip_forecast_jump, temp_forecast_jump, lead_day, latitude, longitude`
(9 features). Max pairwise |correlation| = 0.73 (temp vs. mslp — a real
physical relationship, not redundancy). Excluded on purpose: domain-mean
anomalies (0.95-0.995 correlated with the raw forecast value — redundant),
`hist_bust_*_rate` (a climatological prior, not forecast state — would
double-count the spatial/temporal constraints), `region_v2`/`month` (used
as hard constraints, not distance dimensions). Full reasoning:
`src/phase5/feature_vector.py` module docstring.

## 3. Normalization

z-score, fit on the **2018-2020 TRAIN split only** (`AnalogScaler`) — never
refit on data including the query or test period.

## 4. Distance metric

Standardized Euclidean. Empirically checked against Manhattan (near-
identical) and reasoned against cosine (would call forecasts "similar" by
direction even at very different absolute magnitudes — wrong for physical
analogs). `similarity = 1 / (1 + distance)`, bounded (0,1], no invented
percentage scale.

## 5. Spatial constraints — tested, not assumed

| Constraint | Rain ROC-AUC (retrospective) |
|---|--:|
| same_region | **0.789** (best, with exact_month) |
| nearby (5 nearest region centroids) | 0.711 |
| india_wide | 0.710 |

`same_region` also happened to be the fastest option. Full sweep:
`outputs/phase5/constraint_comparison.csv`.

## 6. Temporal constraints — tested, not assumed

| Constraint | Rain ROC-AUC |
|---|--:|
| exact_month | **0.789** (best) |
| none | 0.643 |
| jjas (any of Jun-Sep) | 0.642 |

Exact month clearly beats a blanket monsoon-season filter — monsoon onset
(June) vs. peak (Jul-Aug) vs. withdrawal (Sep-Oct) are meteorologically
distinct. **Default production config: same_region + exact_month.**

## 7. Leakage prevention

- Similarity vector: forecast-time-only columns (see §2) — never
  `obs_*`/`error_*`/`bust_*`.
- `as_of` cutoff (defaults to the query's own `init_time`): every returned
  analog has `historical_init_time < as_of` — no analog can be from the
  future relative to the case being evaluated.
- `exclude_key`: the exact (init_time, lead_day, lat, lon) of the case
  being evaluated is always excluded from its own candidate pool.
- Outcomes (`actual_precip_mm`, `bust`, etc.) are attached to the top-K
  neighbors **after** they're selected by distance — never used to
  influence which neighbors are chosen.
- Tested explicitly: `tests/test_phase5_analogs.py`
  (`test_current_case_excludes_itself`,
  `test_no_future_analogs_in_retrospective_mode`,
  `test_explicit_as_of_cutoff_is_respected`).

## 8. Index construction

`src/phase5/analogs.py::AnalogIndex` — a standardized feature matrix
(1,786,080 rows × 9 features, ~64MB) + the reference table, no tree
structure (brute-force numpy distance is fast enough — see §Performance).
Build: `python -m src.phase5.build_analog_index`. Load:
`AnalogIndex.load(path)`.

## 9. Query process

`index.query(query_row, k, spatial_constraint, temporal_constraint, as_of,
exclude_key, max_distance, min_analogs)` → over-fetches `3k` candidates,
filters by `max_distance`, returns the closest `k`. `max_distance` defaults
to the region's own empirical 90th-percentile nearest-neighbor distance
(not an arbitrary constant), cached per region.

## 10. Retrospective evaluation

2,000 stratified 2021 test forecasts (200/lead day). Results
(`outputs/phase5/retrospective_comparison.csv`):

| Target | Method | ROC-AUC | PR-AUC | Brier | BSS |
|---|---|--:|--:|--:|--:|
| Rain | Climatology | 0.703 | 0.038 | 0.0183 | -0.004 |
| Rain | Phase 4 ML (frozen) | **0.917** | **0.388** | **0.0128** | **0.301** |
| Rain | Analog-only | 0.789 | 0.044 | 0.0091 | **-0.111** |
| Temp | Climatology | 0.690 | 0.188 | 0.0714 | 0.038 |
| Temp | Phase 4 ML (frozen) | 0.763 | 0.220 | 0.0694 | 0.064 |
| Temp | Analog-only | 0.740 | **0.288** | **0.0683** | **0.094** |

**Honest reading:** analog-only is NOT a replacement for the ML model —
for rain it's badly miscalibrated (negative BSS) despite reasonable
ranking. For **temperature**, analog-only is competitive with and
arguably better-calibrated than the frozen ML model. Correlation(analog
expected |error|, actual |error|): precip=0.458, temp=0.522 — both
meaningfully positive.

## 11. Analog-enhanced experimental model (Stage 11)

Justified by §10's temperature result (and rain's strong ranking despite
poor calibration — an ML model might learn to properly weight it).
Small-scale proof-of-concept (**not** full production scale — computing
analog features for all 1.34M train rows would take ~15 hours; this used
a ~4,000-row stratified train sample instead, so the "baseline" comparison
model here is ALSO trained on that same small sample, isolating the
analog-feature effect rather than confounding it with a data-scale
difference):

| Target | Model | ROC-AUC | Brier | BSS |
|---|---|--:|--:|--:|
| Rain | baseline (no analog) | 0.664 | 0.0085 | -0.036 |
| Rain | + analog features | **0.807** | 0.0084 | -0.016 |
| Temp | baseline (no analog) | 0.720 | 0.0647 | 0.002 |
| Temp | + analog features | **0.790** | **0.0596** | **0.081** |

Saved as `models/phase5/{rain,temp}_v2_experimental.txt` — **NOT** in
`models/registry/`, **NOT** loadable by `src.production.registry`,
**NOT** replacing `rain_v1`/`temperature_v1`. A future phase would need to
retrain at full scale before considering promotion.

## 12. Performance

1.79M-row reference DB. Index build: ~10s. Load (cold process): ~7.5s.
One-time per-region cache warm-up: ~103s (29 regions). Warm-cache query:
~35-45ms regardless of k (5/10/20). Full benchmark:
`outputs/phase5/performance_benchmark.md`. **No FAISS** — brute-force
numpy Euclidean over 1.8M rows is already fast enough; adding an
approximate-neighbor library would be unjustified complexity at this
scale.

## 13. Quality control

- `no_reliable_analogs`: fewer than `min_analogs` (default 5) candidates
  pass the spatial/temporal/`max_distance` filters.
- `low_analog_confidence`: analogs exist but the sample is thin — surfaced
  by `/analog-summary`'s `status` field, never silently upgraded to a
  confident-looking number.
- Verified: an absurdly small `max_distance` (1e-9) and an extreme,
  unrealistic forecast value both correctly trigger `no_reliable_analogs`
  in `tests/test_phase5_analogs.py` / `tests/test_phase5_api.py`.

## 14. Limitations

- JJAS-scope only (same as Phase 2-4) — full-year (e.g. winter western
  disturbance) analogs are not supported; the raw data exists but leak-free
  bust labels were never computed outside JJAS.
- Analog-enhanced model is a small-sample proof-of-concept, not validated
  at production training scale.
- `exact_month` constraint materially reduces analog availability (~43%
  of queries in the retrospective sample got a usable result under
  same_region+exact_month) — a real coverage/quality trade-off, not hidden.
- Region-mapping limitation (Telangana/Ladakh) inherited unchanged from
  Phase 2.
- A real API usability bug was found and fixed during this phase: an
  unsupplied `wind_speed_10m` defaulting to 0.0 (an extreme outlier, real
  range ~0.3-19 m/s) silently broke analog matching for any caller who
  omitted it — now defaults to the train-period mean instead.

## API usage

See `docs/api_contract.md` for `/analogs`, `/analog-summary`,
`/events/{event_id}`, and the restructured `/explain`.
