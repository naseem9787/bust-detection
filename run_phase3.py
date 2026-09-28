"""
Phase 3 orchestrator. Two parts:

1. Data-independent stages (A/B-audit/E/F(0-5)/G/H/I/J/K/L/M/N/O) - run
   these any time; they only need Phase 0-2's already-downloaded data.
2. Data-dependent extensions (F Model 6/7) - run ONLY after
   fetch_atmo_multi_year.sh and src.phase3.ensemble_features have produced
   their files (see each module's docstring for exact paths/commands).

Deliberately NOT a single "run everything" call, because the data-dependent
fetches can take 30-60+ minutes and should be launched explicitly in the
background - see the project's own overnight-run notes for how this was
actually executed.

Usage:
    .venv/Scripts/python.exe run_phase3.py part1
    # ... after fetches complete ...
    .venv/Scripts/python.exe run_phase3.py part2
"""
from __future__ import annotations

import sys

import pandas as pd

from src.phase3 import (
    ablation,
    calibration,
    ensemble_audit,
    event_analysis,
    feature_registry,
    interpretability,
    lead_region_robustness,
    plots,
    replicate_phase2,
    sanity_checks,
    variable_inventory,
    year_robustness,
)


def part1() -> None:
    print("=== A/B: ensemble data audit ===")
    ensemble_audit.main()

    print("\n=== C: variable inventory ===")
    variable_inventory.main()

    print("\n=== D: feature registry ===")
    feature_registry.main()

    print("\n=== E: replicate Phase 2 (CRITICAL - stop if this fails) ===")
    replicate_phase2.main()

    print("\n=== F: ablation study (Models 0-5) ===")
    ablation.main()

    print("\n=== G: year robustness ===")
    year_robustness.run()

    print("\n=== H/I: lead + regional robustness ===")
    lead_region_robustness.main()

    print("\n=== J: calibration ===")
    calibration.main()

    print("\n=== K: event analysis ===")
    event_analysis.main()

    print("\n=== M: interpretability ===")
    interpretability.main()

    print("\n=== N/O: sanity checks + grouped generalization ===")
    sanity_checks.main()

    print("\n=== plots ===")
    plots.main()

    print("\nPart 1 done. Fetch atmo/ensemble data next, then run part2.")


def part2() -> None:
    from src.phase3 import ensemble_pilot_experiment, model6_atmosphere

    print("=== F: Model 6 (atmosphere, full scale) ===")
    model6_atmosphere.run()

    print("\n=== B/F: ensemble pilot experiment (Model 7 + association check) ===")
    ensemble_pilot_experiment.main()

    print("\n=== re-plotting ablation with Models 6/7 ===")
    plots.plot_ablation_incremental(pd.read_csv("outputs/phase3/ablation_results.csv"))
    print(pd.read_csv("outputs/phase3/ablation_results.csv").to_string(index=False))

    print("\nPart 2 done.")


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "part1"
    if part == "part1":
        part1()
    elif part == "part2":
        part2()
    else:
        raise SystemExit("usage: run_phase3.py [part1|part2]")
