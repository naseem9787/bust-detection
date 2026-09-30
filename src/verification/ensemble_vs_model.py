"""
Our rain-bust model vs raw IFS ensemble spread, on identical 2021 hold-out rows.

Ensemble spread (std of the 50-member 24 h rain forecast) is the standard
"how uncertain is this forecast" signal. Both scores are compared by ROC-AUC
and PR-AUC, which are rank-based - spread needs no fitting, so nothing here
touches training data. The difference is bootstrapped over whole forecast
issuances (paired: same resample for both scores).

Also reported, exploratory and fit-free: the average of the two scores'
percentile ranks - does the ensemble add information our model lacks?

Needs: src.verification.ensemble_spread_2021 (data) and
       src.verification.bootstrap_ci (saved test predictions).

Usage:
    .venv/Scripts/python.exe -m src.verification.ensemble_vs_model
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score, roc_auc_score

N_BOOT = 1000
SEED = 7
OUT_DIR = os.path.join("outputs", "verification")
KEYS = ["init_time", "lead_day", "latitude", "longitude"]


def main() -> None:
    ref = pd.read_parquet("models/phase5/reference.parquet",
                          columns=KEYS + ["split", "bust_precip_categorical"])
    ref = ref[ref.split == "test"].reset_index(drop=True)
    ref["model_p"] = np.load(os.path.join(OUT_DIR, "test_pred_rain_v1.npy"))

    ens = pd.read_parquet("data/raw/ens2021/ens_spread_2021_jjas.parquet")
    df = ref.merge(ens, on=KEYS, how="inner")
    print(f"matched rows: {len(df):,} of {len(ref):,} test rows; issuances: {df.init_time.nunique()}")

    y = df.bust_precip_categorical.astype(int).to_numpy()
    scores = {"our_model": df.model_p.to_numpy(), "ensemble_spread": df.ens_std_precip.to_numpy()}
    scores["rank_average_exploratory"] = (rankdata(scores["our_model"]) + rankdata(scores["ensemble_spread"])) / 2

    def auc(s, idx=slice(None)):
        return roc_auc_score(y[idx], s[idx])

    point = {k: {"roc_auc": float(auc(s)), "pr_auc": float(average_precision_score(y, s))} for k, s in scores.items()}

    uniq, inv = np.unique(df.init_time.to_numpy(), return_inverse=True)
    rows_of = [np.flatnonzero(inv == g) for g in range(len(uniq))]
    rng = np.random.default_rng(SEED)
    diffs = {"our_model_minus_spread": [], "rank_average_minus_spread": [], "rank_average_minus_our_model": []}
    for _ in range(N_BOOT):
        idx = np.concatenate([rows_of[g] for g in rng.integers(0, len(uniq), len(uniq))])
        a_m, a_s, a_r = (auc(scores[k], idx) for k in ("our_model", "ensemble_spread", "rank_average_exploratory"))
        diffs["our_model_minus_spread"].append(a_m - a_s)
        diffs["rank_average_minus_spread"].append(a_r - a_s)
        diffs["rank_average_minus_our_model"].append(a_r - a_m)
    delta = {k: {"mean": float(np.mean(v)), "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
             for k, v in diffs.items()}

    by_lead = {}
    for d in sorted(df.lead_day.unique()):
        m = df.lead_day.to_numpy() == d
        by_lead[int(d)] = {k: float(roc_auc_score(y[m], s[m])) for k, s in scores.items()}

    out = {"n_rows": int(len(df)), "n_issuances": int(len(uniq)), "bust_rate": float(y.mean()),
           "method": f"paired block bootstrap over issuances, {N_BOOT} resamples", "point": point,
           "delta_roc_auc": delta, "roc_auc_by_lead_day": by_lead}
    with open(os.path.join(OUT_DIR, "ensemble_vs_model.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"point": point, "delta_roc_auc": delta}, indent=1))


if __name__ == "__main__":
    main()
