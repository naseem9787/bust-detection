"""
Phase 3 - B/F (Model 7): the ensemble + pilot-scope-atmosphere experiment.

Why this is a SEPARATE, smaller experiment rather than folded into the main
ablation study: the ensemble and humidity/geopotential data only exist for
a 21-day pilot window (2021-07-15..2021-08-04), entirely inside the 2021
TEST year - there is ZERO training-period (2018-2020) coverage. A LightGBM
model "trained" on 2018-2020 with these features would see only NaN for
them throughout training and would learn to ignore them entirely - scoring
that model on 2021 and calling the (near-zero) result "ensemble features
don't help" would be a misleading, uninformative conclusion, not a genuine
test of the hypothesis.

Instead, two honest, clearly-scoped checks are run:

1. Direct association (no model needed): within the pilot window, is
   ensemble spread itself correlated with the actual bust outcome? This
   is a legitimate signal check independent of any training-data problem.

2. A small pilot-scale chronological experiment: the pilot window's own
   21 days are split internally (first 14 days = pilot-train, last 7 days
   = pilot-test - still chronological, still no random split), so LightGBM
   gets SOME non-null exposure to these features during training. Sample
   size is tiny (roughly a few thousand rows) - reported with an explicit
   small-sample caveat, not presented as being as rigorous as the main
   2018-2020/2021 experiments.

Usage (after both fetch_atmo_multi_year.sh's `levels` step and
src.phase3.ensemble_features have produced their pilot files):
    .venv/Scripts/python.exe -m src.phase3.ensemble_pilot_experiment
"""
from __future__ import annotations

import os

import pandas as pd
from scipy import stats

from ..phase2.features import TARGET_COLS
from . import modeling
from .ablation import GROUP5
from .atmo_merge import LEVEL_FEATURE_COLS, WIND_FEATURE_COLS, load_levels_dataframe, load_wind_dataframe
from .data_assembly import build_full_domain_base
from .ensemble_features import PILOT_END, PILOT_START, build_or_load_pilot

OUT_DIR = os.path.join("outputs", "phase3")

ENSEMBLE_FEATURE_COLS = [
    "ensemble_mean_precip", "ensemble_std_precip", "ensemble_min_precip",
    "ensemble_max_precip", "ensemble_iqr_precip", "ensemble_cv_precip",
    "ensemble_mean_temp", "ensemble_std_temp", "ensemble_min_temp",
    "ensemble_max_temp", "ensemble_iqr_temp",
    "domain_mean_ensemble_std_precip", "domain_mean_ensemble_std_temp",
]

PILOT_SPLIT_DATE = "2021-07-29"  # 14 days train (07-15..07-28), 7 days test (07-29..08-04)


def build_pilot_dataset() -> pd.DataFrame:
    base = build_full_domain_base()
    pilot = base[
        (base.init_time >= pd.Timestamp(PILOT_START)) & (base.init_time <= pd.Timestamp(PILOT_END) + pd.Timedelta(hours=23))
    ].copy()

    wind = load_wind_dataframe([2021])
    pilot = pilot.merge(wind, on=["init_time", "lead_day", "latitude", "longitude"], how="left")

    levels = load_levels_dataframe()
    pilot = pilot.merge(levels, on=["init_time", "lead_day", "latitude", "longitude"], how="left")

    ens = build_or_load_pilot()
    pilot = pilot.merge(ens, on=["init_time", "lead_day", "latitude", "longitude"], how="left", suffixes=("", "_ens"))

    keep_cols = WIND_FEATURE_COLS + LEVEL_FEATURE_COLS + ENSEMBLE_FEATURE_COLS
    n_before = len(pilot)
    pilot = pilot.dropna(subset=keep_cols)
    print(f"pilot rows with complete new-feature coverage: {len(pilot):,}/{n_before:,}")

    from .data_assembly import build_experiment_features  # local import to avoid unused-at-import cost
    # historical features still need a proper train-only fit - use the SAME
    # main-experiment train/test split (2018-2020/2021) for THAT part, since
    # historical climatology genuinely benefits from more years, unlike the
    # brand-new pilot-only features.
    full_train, _ = build_experiment_features(base, [2018, 2019, 2020], 2021)
    from ..phase2.features import fit_historical_features, apply_historical_features
    fitted = fit_historical_features(full_train)
    pilot = apply_historical_features(pilot, fitted)
    return pilot


def association_check(pilot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pairs = [
        ("bust_precip_categorical", "ensemble_std_precip"),
        ("bust_precip_categorical", "domain_mean_ensemble_std_precip"),
        ("bust_temp_hard", "ensemble_std_temp"),
        ("bust_temp_hard", "domain_mean_ensemble_std_temp"),
    ]
    for target, feature in pairs:
        y = pilot[target].astype(int)
        x = pilot[feature]
        r, p = stats.pointbiserialr(y, x)
        rows.append(
            {
                "target": target,
                "ensemble_feature": feature,
                "n": len(pilot),
                "point_biserial_r": r,
                "p_value": p,
                "mean_when_bust": float(x[y == 1].mean()) if (y == 1).any() else float("nan"),
                "mean_when_no_bust": float(x[y == 0].mean()) if (y == 0).any() else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def pilot_scale_model_experiment(pilot: pd.DataFrame) -> pd.DataFrame:
    pilot_train = pilot[pilot.init_time < pd.Timestamp(PILOT_SPLIT_DATE)]
    pilot_test = pilot[pilot.init_time >= pd.Timestamp(PILOT_SPLIT_DATE)]
    print(f"pilot-train n={len(pilot_train):,} ({pilot_train.init_time.min()}..{pilot_train.init_time.max()})")
    print(f"pilot-test n={len(pilot_test):,} ({pilot_test.init_time.min()}..{pilot_test.init_time.max()})")

    rows = []
    for target in TARGET_COLS:
        reference_prob = float(pilot_train[target].mean())
        if pilot_train[target].nunique() < 2 or pilot_test[target].nunique() < 2:
            print(f"  {target}: insufficient class variation in this tiny pilot split - skipping")
            continue

        for name, cols in [
            ("Model5_SpatialAnomaly_pilot_subset", GROUP5),
            (
                "Model7_Ensemble_pilot_subset",
                GROUP5 + WIND_FEATURE_COLS + LEVEL_FEATURE_COLS + ENSEMBLE_FEATURE_COLS,
            ),
        ]:
            res = modeling.train_lgbm_fixed(pilot_train, pilot_test, target, cols, n_estimators=100)
            metrics = modeling.score(res["y_test"], res["y_prob"], reference_prob, reference_prob)
            rows.append({"model": name, "target": target, "n_features": len(cols), **metrics})
            print(f"  {name} / {target}: n_test={metrics['n']} ROC-AUC={metrics['roc_auc']:.4f} "
                  f"PR-AUC={metrics['pr_auc']:.4f}")

    return pd.DataFrame(rows)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    pilot = build_pilot_dataset()

    assoc = association_check(pilot)
    assoc_path = os.path.join(OUT_DIR, "ensemble_association_check.csv")
    assoc.to_csv(assoc_path, index=False)
    print(f"saved -> {assoc_path}")
    print(assoc.to_string(index=False))

    model_results = pilot_scale_model_experiment(pilot)
    if not model_results.empty:
        path = os.path.join(OUT_DIR, "ensemble_pilot_model_results.csv")
        model_results.to_csv(path, index=False)
        print(f"\nsaved -> {path}")

        # also append Model7 rows to the main ablation_results.csv, clearly
        # tagged as pilot-subset so readers don't compare n directly to Models 0-6
        ablation_path = os.path.join(OUT_DIR, "ablation_results.csv")
        if os.path.exists(ablation_path):
            existing = pd.read_csv(ablation_path)
            existing = existing[~existing.model.isin(model_results.model.unique())]
            combined = pd.concat([existing, model_results], ignore_index=True)
            combined.to_csv(ablation_path, index=False)
            print(f"appended pilot-subset rows to -> {ablation_path}")


if __name__ == "__main__":
    main()
