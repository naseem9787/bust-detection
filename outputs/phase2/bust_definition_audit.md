# Phase 2 Bust-Definition Audit

Documents exactly how each Phase-0/1 bust component is constructed (unchanged from Phase 0/1), then scores candidate predictive targets for Phase 2B. See src/phase2/bust_definition_audit.py for the exact computation - this file is generated, not hand-written.

## Component construction

| Component | Variable | Threshold | Type | Percentile-based | Grouping | Fitting period | Train-only fit | Expected prevalence |
|---|---|---|---|---|---|---|---|---|
| bust_precip_categorical | total_precipitation_24hr | IMD category gap >= 2, or heavy-or-above missed/false-alarmed | fixed (IMD operational bins, mm/day) | False | none (bins are universal, not fit per group) | not applicable - fixed physical bins | not applicable (nothing is fit) | low (~1%) - category misses by >=2 steps are rare |
| bust_temp_hard | 2m_temperature | 3.0 degC absolute error | fixed constant | False | none | not applicable - fixed constant | not applicable (nothing is fit) | moderate (~7-8%) |
| bust_precip_percentile | total_precipitation_24hr | 90% percentile of |error| per (region, lead_day) | data-derived percentile | True | region, lead_day | train split (2018-2020) only | True | ~10% in every (region, lead_day) bucket, BY CONSTRUCTION |
| bust_temp_percentile | 2m_temperature | 90% percentile of |error| per (region, lead_day) | data-derived percentile | True | region, lead_day | train split (2018-2020) only | True | ~10% in every (region, lead_day) bucket, BY CONSTRUCTION |
| bust_mslp_percentile | mean_sea_level_pressure | 90% percentile of |error| per (region, lead_day) | data-derived percentile | True | region, lead_day | train split (2018-2020) only | True | ~10% in every (region, lead_day) bucket, BY CONSTRUCTION |
| bust_any | all three (OR of all 5 flags above) | n/a - logical OR | composite | partially (3 of 5 inputs) | n/a | inherits from its components | True | ~25-27% (dominated by the 3 near-flat percentile flags) |

## Candidate labels - empirical scoring (train-only-fit climatology, 2021 holdout)

| Candidate | Type | Prevalence (train) | Prevalence (test) | ROC-AUC | PR-AUC | Brier | R2 | Corr |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bust_precip_categorical | binary | 0.0133 | 0.0106 | 0.6858 | 0.0237 | 0.0104 | - | - |
| bust_temp_hard | binary | 0.0814 | 0.0715 | 0.6730 | 0.1274 | 0.0649 | - | - |
| abs_error_temp_c | continuous | 1.2454 | 1.1866 | - | - | - | 0.0642 | 0.2603 |
| bust_categorical_or_temp_hard | binary | 0.0931 | 0.0809 | 0.6650 | 0.1397 | 0.0726 | - | - |

## Verdict

Not picked by AUC alone - weighing prevalence (enough positives to model),
operational relevance (the SIH problem statement names heavy-rainfall events
AND heat waves as target failure modes), and physical defensibility:

- **Candidate A** (`bust_precip_categorical`) and **Candidate B** (`bust_temp_hard`) both show real climatological structure (ROC-AUC 0.67-0.69 from region x lead x month history ALONE, before any forecast-time features) - a genuine signal Phase 2B's LightGBM model should be able to improve on with richer features.
- Candidate C (continuous error) is reported for context only - not modeled with LightGBM this pass (classification is the more direct match to the SIH deliverable 'bust probability'; a regression head is a reasonable Phase 3 addition).
- Candidate D (A|B composite) is evaluated for completeness below, but per the instructions' own preference, Phase 2B trains SEPARATE models for A and B rather than combining them - they represent physically distinct failure modes (rainfall vs. temperature) with different regional footprints (see outputs/phase2/plots/component_rate_by_region.png), and combining them would re-introduce the same signal-diluting effect that made bust_any hard to predict.
- **Decision: Phase 2B trains two separate LightGBM models - one for Candidate A, one for Candidate B.**