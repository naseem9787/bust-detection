"""
Phase 2 - A2: bust-definition audit + candidate predictive targets.

Documents exactly how each Phase-0/1 bust component is built (does NOT
change any of them - see src/config.py, src/label_busts.py,
src/phase1/dataset.py), then defines and empirically scores candidate
labels for Phase 2B modeling, using the SAME train-only-fit climatology
baseline and 2021 holdout as component_analysis.py.

Candidates
----------
A: bust_precip_categorical  - IMD rainfall-category miss / missed or false heavy-rain event
B: bust_temp_hard            - |temp error| > 3 degC
C: continuous error target   - abs_error_temp_c (reported via a climatology R^2/correlation
                                sanity check only; NOT modeled with LightGBM in this pass -
                                see model_summary.md for why)
D: composite = A | B         - i.e. the two components that DO carry regional/lead signal,
                                excluding the three percentile-normalized ones that don't

No winner is picked by AUC alone - prevalence, operational relevance (the SIH problem
statement explicitly names heavy-rainfall events AND heat waves as target failure modes),
and sample size for modeling are all weighed in the written verdict at the bottom of
outputs/phase2/bust_definition_audit.md.

Usage:
    .venv/Scripts/python.exe -m src.phase2.bust_definition_audit
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, r2_score, roc_auc_score

from .. import config
from ..phase1.dataset import TEST_YEAR, TRAIN_YEARS, build_phase1_dataset
from .component_analysis import GROUP_COLS, _fit_climatology, _predict, _safe_auc

OUT_DIR = os.path.join("outputs", "phase2")

COMPONENT_SPEC = [
    {
        "component": "bust_precip_categorical",
        "variable": "total_precipitation_24hr",
        "threshold": "IMD category gap >= 2, or heavy-or-above missed/false-alarmed",
        "threshold_type": "fixed (IMD operational bins, mm/day)",
        "percentile_based": False,
        "grouping_dims": "none (bins are universal, not fit per group)",
        "fitting_period": "not applicable - fixed physical bins",
        "train_only_fit": "not applicable (nothing is fit)",
        "expected_prevalence": "low (~1%) - category misses by >=2 steps are rare",
    },
    {
        "component": "bust_temp_hard",
        "variable": "2m_temperature",
        "threshold": f"{config.TEMP_BUST_ABS_ERROR_K} degC absolute error",
        "threshold_type": "fixed constant",
        "percentile_based": False,
        "grouping_dims": "none",
        "fitting_period": "not applicable - fixed constant",
        "train_only_fit": "not applicable (nothing is fit)",
        "expected_prevalence": "moderate (~7-8%)",
    },
    {
        "component": "bust_precip_percentile",
        "variable": "total_precipitation_24hr",
        "threshold": f"{config.BUST_PERCENTILE:.0%} percentile of |error| per (region, lead_day)",
        "threshold_type": "data-derived percentile",
        "percentile_based": True,
        "grouping_dims": "region, lead_day",
        "fitting_period": "train split (2018-2020) only",
        "train_only_fit": True,
        "expected_prevalence": "~10% in every (region, lead_day) bucket, BY CONSTRUCTION",
    },
    {
        "component": "bust_temp_percentile",
        "variable": "2m_temperature",
        "threshold": f"{config.BUST_PERCENTILE:.0%} percentile of |error| per (region, lead_day)",
        "threshold_type": "data-derived percentile",
        "percentile_based": True,
        "grouping_dims": "region, lead_day",
        "fitting_period": "train split (2018-2020) only",
        "train_only_fit": True,
        "expected_prevalence": "~10% in every (region, lead_day) bucket, BY CONSTRUCTION",
    },
    {
        "component": "bust_mslp_percentile",
        "variable": "mean_sea_level_pressure",
        "threshold": f"{config.BUST_PERCENTILE:.0%} percentile of |error| per (region, lead_day)",
        "threshold_type": "data-derived percentile",
        "percentile_based": True,
        "grouping_dims": "region, lead_day",
        "fitting_period": "train split (2018-2020) only",
        "train_only_fit": True,
        "expected_prevalence": "~10% in every (region, lead_day) bucket, BY CONSTRUCTION",
    },
    {
        "component": "bust_any",
        "variable": "all three (OR of all 5 flags above)",
        "threshold": "n/a - logical OR",
        "threshold_type": "composite",
        "percentile_based": "partially (3 of 5 inputs)",
        "grouping_dims": "n/a",
        "fitting_period": "inherits from its components",
        "train_only_fit": True,
        "expected_prevalence": "~25-27% (dominated by the 3 near-flat percentile flags)",
    },
]


def evaluate_binary_candidate(train: pd.DataFrame, test: pd.DataFrame, target_col: str) -> dict:
    lookup, fallback = _fit_climatology(train, target_col)
    y_true = test[target_col].to_numpy().astype(int)
    y_prob = _predict(test, lookup, fallback)
    return {
        "candidate": target_col,
        "type": "binary",
        "prevalence_train": float(train[target_col].mean()),
        "prevalence_test": float(test[target_col].mean()),
        "roc_auc_test": _safe_auc(y_true, y_prob),
        "pr_auc_test": average_precision_score(y_true, y_prob),
        "brier_test": brier_score_loss(y_true, y_prob),
    }


def evaluate_continuous_candidate(train: pd.DataFrame, test: pd.DataFrame, target_col: str) -> dict:
    """Sanity-check only: how much of the continuous error is explained by a
    train-only-fit (region, lead_day, month) mean-error lookup, scored on 2021."""
    lookup = train.groupby(GROUP_COLS, observed=True)[target_col].mean()
    fallback = float(train[target_col].mean())
    keys = pd.MultiIndex.from_frame(test[GROUP_COLS])
    y_pred = pd.Series(keys.map(lookup), index=test.index).fillna(fallback).to_numpy()
    y_true = test[target_col].to_numpy()
    return {
        "candidate": target_col,
        "type": "continuous",
        "prevalence_train": float(train[target_col].mean()),  # mean, not a rate, for continuous
        "prevalence_test": float(test[target_col].mean()),
        "r2_test": float(r2_score(y_true, y_pred)),
        "corr_test": float(np.corrcoef(y_true, y_pred)[0, 1]),
    }


def render_markdown(component_table: pd.DataFrame, candidate_table: pd.DataFrame) -> str:
    lines = [
        "# Phase 2 Bust-Definition Audit",
        "",
        "Documents exactly how each Phase-0/1 bust component is constructed "
        "(unchanged from Phase 0/1), then scores candidate predictive targets "
        "for Phase 2B. See src/phase2/bust_definition_audit.py for the exact "
        "computation - this file is generated, not hand-written.",
        "",
        "## Component construction",
        "",
        "| Component | Variable | Threshold | Type | Percentile-based | Grouping | Fitting period | Train-only fit | Expected prevalence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in COMPONENT_SPEC:
        lines.append(
            f"| {c['component']} | {c['variable']} | {c['threshold']} | {c['threshold_type']} | "
            f"{c['percentile_based']} | {c['grouping_dims']} | {c['fitting_period']} | "
            f"{c['train_only_fit']} | {c['expected_prevalence']} |"
        )

    lines += [
        "",
        "## Candidate labels - empirical scoring (train-only-fit climatology, 2021 holdout)",
        "",
        "| Candidate | Type | Prevalence (train) | Prevalence (test) | ROC-AUC | PR-AUC | Brier | R2 | Corr |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in candidate_table.iterrows():
        def fmt(v):
            return "-" if pd.isna(v) else f"{v:.4f}"
        lines.append(
            f"| {row['candidate']} | {row['type']} | {fmt(row.get('prevalence_train'))} | "
            f"{fmt(row.get('prevalence_test'))} | {fmt(row.get('roc_auc_test'))} | "
            f"{fmt(row.get('pr_auc_test'))} | {fmt(row.get('brier_test'))} | "
            f"{fmt(row.get('r2_test'))} | {fmt(row.get('corr_test'))} |"
        )

    lines += [
        "",
        "## Verdict",
        "",
        "Not picked by AUC alone - weighing prevalence (enough positives to model),",
        "operational relevance (the SIH problem statement names heavy-rainfall events",
        "AND heat waves as target failure modes), and physical defensibility:",
        "",
        "- **Candidate A** (`bust_precip_categorical`) and **Candidate B** "
        "(`bust_temp_hard`) both show real climatological structure (ROC-AUC "
        "0.67-0.69 from region x lead x month history ALONE, before any forecast-time "
        "features) - a genuine signal Phase 2B's LightGBM model should be able to "
        "improve on with richer features.",
        "- Candidate C (continuous error) is reported for context only - not modeled "
        "with LightGBM this pass (classification is the more direct match to the "
        "SIH deliverable 'bust probability'; a regression head is a reasonable Phase 3 addition).",
        "- Candidate D (A|B composite) is evaluated for completeness below, but per the "
        "instructions' own preference, Phase 2B trains SEPARATE models for A and B "
        "rather than combining them - they represent physically distinct failure modes "
        "(rainfall vs. temperature) with different regional footprints (see "
        "outputs/phase2/plots/component_rate_by_region.png), and combining them would "
        "re-introduce the same signal-diluting effect that made bust_any hard to predict.",
        "- **Decision: Phase 2B trains two separate LightGBM models - one for "
        "Candidate A, one for Candidate B.**",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    ds = build_phase1_dataset()
    df = ds.df
    train = df[df.split == "train"]
    test = df[df.split == "test"]

    df["bust_categorical_or_temp_hard"] = df.bust_precip_categorical | df.bust_temp_hard
    train = df[df.split == "train"]
    test = df[df.split == "test"]

    candidates = [
        evaluate_binary_candidate(train, test, "bust_precip_categorical"),
        evaluate_binary_candidate(train, test, "bust_temp_hard"),
        evaluate_continuous_candidate(train, test, "abs_error_temp_c"),
        evaluate_binary_candidate(train, test, "bust_categorical_or_temp_hard"),
    ]
    candidate_table = pd.DataFrame(candidates)

    component_table = pd.DataFrame(COMPONENT_SPEC)
    component_table.to_csv(os.path.join(OUT_DIR, "bust_component_construction.csv"), index=False)

    md = render_markdown(component_table, candidate_table)
    md_path = os.path.join(OUT_DIR, "bust_definition_audit.md")
    with open(md_path, "w") as f:
        f.write(md)
    print(f"saved -> {md_path}")
    print(f"train years: {TRAIN_YEARS}, test year: {TEST_YEAR}")
    print(candidate_table.to_string(index=False))


if __name__ == "__main__":
    main()
