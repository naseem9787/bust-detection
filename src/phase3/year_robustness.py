"""
Phase 3 - G: robustness across years. Three chronological experiments, each
with its OWN train-only-fit historical features (never reusing another
experiment's fit - see data_assembly.build_experiment_features). No random
splitting anywhere; no experiment is tuned on its own test year.

Experiments:
  1. train 2018-2019 -> test 2020
  2. train 2018-2020 -> test 2021  (= the original Phase 2 experiment)
  3. train 2019-2020 -> test 2021

For each: fit_years = train_years[:-1], val_year = train_years[-1] (early
stopping only), final model refit on all of train_years.

Usage:
    .venv/Scripts/python.exe -m src.phase3.year_robustness
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import FEATURE_COLS, TARGET_COLS
from . import modeling
from .data_assembly import build_experiment_features, build_full_domain_base

OUT_DIR = os.path.join("outputs", "phase3")

EXPERIMENTS = [
    ("Exp1_train1819_test20", [2018, 2019], 2020),
    ("Exp2_train181920_test21", [2018, 2019, 2020], 2021),
    ("Exp3_train1920_test21", [2019, 2020], 2021),
]


def run() -> pd.DataFrame:
    base = build_full_domain_base()
    rows = []
    for exp_name, train_years, test_year in EXPERIMENTS:
        fit_years = train_years[:-1]
        val_year = train_years[-1]
        print(f"\n=== {exp_name}: train={train_years} (fit={fit_years}, val={val_year}) test={test_year} ===")
        train, test = build_experiment_features(base, train_years, test_year)

        for target in TARGET_COLS:
            reference_prob = float(train[target].mean())
            res = modeling.train_lgbm(
                train, test, target, FEATURE_COLS, fit_years=fit_years, val_year=val_year
            )
            metrics = modeling.score(res["y_test"], res["y_prob"], reference_prob, reference_prob)
            row = {
                "experiment": exp_name,
                "train_years": str(train_years),
                "test_year": test_year,
                "target": target,
                "best_iteration": res["best_iteration"],
                **metrics,
            }
            rows.append(row)
            print(f"  {target}: n={row['n']:,} prevalence={row['prevalence']:.3f} "
                  f"ROC-AUC={row['roc_auc']:.4f} PR-AUC={row['pr_auc']:.4f} "
                  f"Brier={row['brier_score']:.4f} BSS={row['brier_skill_score']:.4f}")

    result = pd.DataFrame(rows)
    path = os.path.join(OUT_DIR, "year_robustness.csv")
    os.makedirs(OUT_DIR, exist_ok=True)
    result.to_csv(path, index=False)
    print(f"\nsaved -> {path}")
    return result


if __name__ == "__main__":
    run()
