"""
Phase 2 - Part C deliverable: model_summary.md, assembled from the already-
generated outputs (not hand-written prose disconnected from the numbers).

Usage:
    .venv/Scripts/python.exe -m src.phase2.model_summary
"""
from __future__ import annotations

import json
import os

import pandas as pd

from .features import FEATURE_COLS, OUT_DIR, TARGET_COLS


def render_target_section(target: str, config: dict, comparison: pd.DataFrame,
                           importance: pd.DataFrame, calibration: pd.DataFrame,
                           per_lead: pd.DataFrame, per_region: pd.DataFrame) -> list[str]:
    tconf = config["targets"][target]
    comp = comparison[comparison.target == target]
    imp = importance[importance.target == target].sort_values("gain", ascending=False)
    cal = calibration[calibration.target == target].iloc[0]
    lead = per_lead[per_lead.target == target].sort_values("lead_day")
    region = per_region[per_region.target == target].sort_values("roc_auc", ascending=False)

    lines = [f"## Target: `{target}`", ""]
    lines.append(
        f"- Train prevalence: {tconf['train_prevalence']:.2%}, "
        f"Test (2021) prevalence: {tconf['test_prevalence']:.2%}"
    )
    lines.append(
        f"- Fit years {config['fit_years']} -> validate on {config['val_year']} "
        f"(early stopping only, best_iteration={tconf['best_iteration']}) -> "
        f"final model refit on {tconf['train_years'] if 'train_years' in tconf else '2018-2020'} "
        f"with that fixed tree count -> scored ONCE on {config['test_year']}"
    )
    lines.append(f"- n_fit={tconf['n_fit']:,}, n_val={tconf['n_val']:,}, "
                  f"n_train_final={tconf['n_train_final']:,}, n_test={tconf['n_test']:,}")
    lines += ["", "### Results (2021 holdout)", "", comp[[
        "method", "roc_auc", "pr_auc", "brier_score", "brier_skill_score",
        "precision", "recall", "f1", "false_alarm_rate", "miss_rate",
    ]].round(4).to_markdown(index=False), ""]

    lines += ["### Top 5 features (gain importance)", "",
              imp.head(5)[["feature", "gain", "split"]].to_markdown(index=False), ""]

    lines += [
        "### Calibration", "",
        f"- Brier (raw): {cal.brier_raw:.4f}, Brier (isotonic-calibrated, fit on "
        f"2020 validation predictions): {cal.brier_calibrated:.4f}",
        f"- Calibration {'IMPROVED' if cal.calibration_improved else 'did NOT improve'} "
        f"the Brier score -> confidence_score.py uses "
        f"{'the calibrated' if cal.calibration_improved else 'the raw'} probability for this target",
        "",
    ]

    lines += ["### Lead-time behaviour", "",
              lead[["lead_day", "n", "prevalence", "roc_auc", "pr_auc", "brier"]].to_markdown(index=False), ""]

    lines += ["### Regional behaviour (top 5 by ROC-AUC, min 20 samples)", "",
              region[region.n >= 20].head(5)[
                  ["region_v2", "n", "prevalence", "roc_auc", "pr_auc"]
              ].to_markdown(index=False), ""]

    return lines


def main() -> None:
    with open(os.path.join(OUT_DIR, "model_training_config.json")) as f:
        config = json.load(f)
    comparison = pd.read_csv(os.path.join(OUT_DIR, "model_comparison.csv"))
    importance = pd.read_csv(os.path.join(OUT_DIR, "feature_importance.csv"))
    calibration = pd.read_csv(os.path.join(OUT_DIR, "calibration_summary.csv"))
    per_lead = pd.read_csv(os.path.join(OUT_DIR, "per_lead_metrics.csv"))
    per_region = pd.read_csv(os.path.join(OUT_DIR, "per_region_metrics.csv"))

    lines = [
        "# Phase 2 Model Summary",
        "",
        "First real predictive model: LightGBM, trained separately for the two "
        "candidate targets identified in Phase 2A's bust-definition audit "
        "(`outputs/phase2/bust_definition_audit.md`) - NOT the diluted "
        "`bust_any` composite (see Phase 1/2A findings for why).",
        "",
        f"Features used ({len(FEATURE_COLS)}): " + ", ".join(f"`{c}`" for c in FEATURE_COLS),
        "",
        "Train/val/test split is chronological throughout: fit on "
        f"{config['fit_years']}, validate (early stopping only) on "
        f"{config['val_year']}, final model refit on all of 2018-2020, "
        f"scored once on {config['test_year']} - the same split Phase 1 used, "
        "never touched during model/hyperparameter selection.",
        "",
        f"Random seed: {config['random_seed']}. LightGBM params: "
        f"{json.dumps(config['base_params'])}",
        "",
    ]

    for target in TARGET_COLS:
        lines += render_target_section(
            target, config, comparison, importance, calibration, per_lead, per_region
        )

    lines += [
        "## Limitations",
        "",
        "- Ensemble spread features are unavailable this pass (see "
        "`outputs/phase2/feature_availability.md`) - the model relies on a "
        "single deterministic forecast, historical climatology, and simple "
        "derived features (anomaly vs. domain mean, run-to-run forecast jump).",
        "- Wind, humidity, and geopotential height are available in the "
        "source data but not yet downloaded/used - a natural next step.",
        "- The geography fix (Part A3) covers 183 of 702 grid points (the "
        "actual India domain); 29 regions, some with very few grid points "
        "at 1.5-degree resolution, so per-region metrics for small regions "
        "should be read with their sample size in mind.",
        "- `bust_precip_categorical`'s very high test ROC-AUC (~0.91) was "
        "specifically checked for leakage (see `outputs/phase2/leakage_audit.csv`) "
        "- no leakage mechanism was found, and the effect is physically "
        "explainable (the forecast's own precipitation value is the top "
        "feature - larger forecast values carry more inherent uncertainty), "
        "with a smooth, expected decay across lead days rather than a flat "
        "or perfect score. Still flagged here for independent replication "
        "before being trusted operationally.",
        "- Two SEPARATE models, not one combined bust predictor - per Phase "
        "2A's finding that combining these two candidate targets measurably "
        "dilutes signal (see bust_definition_audit.md Candidate D).",
    ]

    path = os.path.join(OUT_DIR, "model_summary.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
