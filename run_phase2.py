"""
Phase 2 orchestrator - Part A (bust component analysis, definition audit,
geography fix, feature/leakage audit) then Part B (feature table, LightGBM,
evaluation, event analysis) then Part C (confidence score, model summary).

Requires Phase 0/1 to have already produced data/processed/error_db.parquet
(see fetch_multi_year.sh 2018 2021) and data/raw/india_states.geojson (see
src/phase2/geography.py's docstring for the fetch command).

Usage:
    .venv/Scripts/python.exe run_phase2.py
"""
from __future__ import annotations

from src.phase2 import (
    bust_definition_audit,
    component_analysis,
    confidence_score,
    event_analysis,
    evaluate_model,
    feature_inventory,
    features,
    geography,
    leakage_audit,
    model_summary,
    train_model,
)


def main() -> None:
    print("=== Part A1: bust component analysis ===")
    component_analysis.main()

    print("\n=== Part A2: bust-definition audit ===")
    bust_definition_audit.main()

    print("\n=== Part A3: geographic assignment fix ===")
    geography.main()

    print("\n=== Part A4: feature availability ===")
    feature_inventory.main()

    print("\n=== Part A5: leakage audit ===")
    leakage_audit.main()

    print("\n=== Part B1: feature table ===")
    features.main()

    print("\n=== Part B2: LightGBM training ===")
    train_model.main()

    print("\n=== Part B3-B7: evaluation (baselines, importance, calibration, lead/region) ===")
    evaluate_model.main()

    print("\n=== Part B8: event-level analysis ===")
    event_analysis.main()

    print("\n=== Part C: confidence score + model summary ===")
    confidence_score.main()
    model_summary.main()

    print("\nDone. See outputs/phase2/ for all deliverables.")


if __name__ == "__main__":
    main()
