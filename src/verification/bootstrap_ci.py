"""
95% confidence intervals for the 2021 hold-out metrics of the production
models (rain_v1, temperature_v1).

Rows that share a forecast issuance (init_time) are strongly correlated - one
weather situation covers the whole map - so resampling individual rows would
overstate precision. This is a block bootstrap: resample the 244 issuances
of JJAS 2021 with replacement, and take every row of each drawn issuance.

Brier Skill Score uses the same reference as the registry numbers: the
sample climatology (bust rate of the evaluated rows).

Usage:
    .venv/Scripts/python.exe -m src.verification.bootstrap_ci
"""
from __future__ import annotations

import json
import os
import pickle

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ..production.features import region_categories

N_BOOT = 1000
SEED = 42
OUT_DIR = os.path.join("outputs", "verification")
MODELS = {"rain_v1": "bust_precip_categorical", "temperature_v1": "bust_temp_hard"}


def load_test() -> pd.DataFrame:
    df = pd.read_parquet("models/phase5/reference.parquet")
    df = df[df.split == "test"].reset_index(drop=True)
    df["region_v2"] = df["region_v2"].astype(region_categories())
    return df


def predict(df: pd.DataFrame, model_name: str) -> np.ndarray:
    reg = json.load(open(f"models/registry/{model_name}.json"))
    booster = lgb.Booster(model_file=reg["model_artifact_path"])
    p = booster.predict(df[reg["feature_order"]])
    cal = reg["calibration"]["artifact_path"]
    if cal:
        with open(cal.replace("\\", "/"), "rb") as f:
            p = pickle.load(f).predict(p)
    return np.clip(p, 0.0, 1.0)


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    brier = float(np.mean((p - y) ** 2))
    base = y.mean()
    return {"roc_auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
            "brier": brier, "bss": 1.0 - brier / float(base * (1.0 - base)), "prevalence": float(base)}


def block_bootstrap(y: np.ndarray, p: np.ndarray, groups: np.ndarray, rng) -> dict:
    uniq, inv = np.unique(groups, return_inverse=True)
    rows_of = [np.flatnonzero(inv == g) for g in range(len(uniq))]
    draws = {k: [] for k in ("roc_auc", "pr_auc", "brier", "bss")}
    for _ in range(N_BOOT):
        idx = np.concatenate([rows_of[g] for g in rng.integers(0, len(uniq), len(uniq))])
        m = metrics(y[idx], p[idx])
        for k in draws:
            draws[k].append(m[k])
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in draws.items()}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_test()
    rng = np.random.default_rng(SEED)
    out = {"method": f"block bootstrap over forecast issuances (init_time), {N_BOOT} resamples, 95% percentile interval",
           "n_rows": int(len(df)), "n_issuances": int(df.init_time.nunique()), "models": {}}
    for model_name, target in MODELS.items():
        p = predict(df, model_name)
        y = df[target].astype(int).to_numpy()
        point = metrics(y, p)
        ci = block_bootstrap(y, p, df.init_time.to_numpy(), rng)
        by_lead = {int(d): metrics(y[m], p[m])["roc_auc"] for d in sorted(df.lead_day.unique())
                   for m in [df.lead_day.to_numpy() == d]}
        out["models"][model_name] = {"target": target, "point": point, "ci95": ci, "roc_auc_by_lead_day": by_lead}
        np.save(os.path.join(OUT_DIR, f"test_pred_{model_name}.npy"), p)
        print(f"{model_name}: ROC-AUC {point['roc_auc']:.3f} [{ci['roc_auc'][0]:.3f}, {ci['roc_auc'][1]:.3f}]  "
              f"PR-AUC {point['pr_auc']:.3f} [{ci['pr_auc'][0]:.3f}, {ci['pr_auc'][1]:.3f}]  "
              f"BSS {point['bss']:.3f} [{ci['bss'][0]:.3f}, {ci['bss'][1]:.3f}]", flush=True)
    with open(os.path.join(OUT_DIR, "bootstrap_ci.json"), "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()
