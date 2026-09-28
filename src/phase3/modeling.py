"""
Phase 3 - shared modeling utility: a generalized version of
src.phase2.train_model.train_one_target, parameterized by feature list and
train/test frames, so Stages F (ablation), G (year robustness), H (lead
robustness) and I (region robustness) don't each reimplement training.

Does not modify src/phase2/train_model.py - this is an additive, more
general sibling used only by Phase 3 scripts.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

RANDOM_SEED = 42
FIT_YEARS = [2018, 2019]
VAL_YEAR = 2020
MAX_ESTIMATORS = 1000
EARLY_STOPPING_ROUNDS = 50
BASE_PARAMS = dict(
    objective="binary",
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=200,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    random_state=RANDOM_SEED,
    n_jobs=-1,
    verbosity=-1,
)


def train_lgbm(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    feature_cols: list[str],
    fit_years: list[int] = FIT_YEARS,
    val_year: int = VAL_YEAR,
) -> dict:
    """Same procedure as Phase 2's train_one_target: fit on `fit_years`,
    early-stop on `val_year`, refit final model on all of `train` with the
    resulting fixed tree count, score once on `test`. `test` is NEVER used
    for hyperparameter/tree-count selection."""
    fit_df = train[train.init_time.dt.year.isin(fit_years)]
    val_df = train[train.init_time.dt.year == val_year]
    assert len(fit_df) > 0 and len(val_df) > 0, "empty fit/val split - check year filters"

    X_fit, y_fit = fit_df[feature_cols], fit_df[target].astype(int)
    X_val, y_val = val_df[feature_cols], val_df[target].astype(int)

    probe = lgb.LGBMClassifier(n_estimators=MAX_ESTIMATORS, **BASE_PARAMS)
    probe.fit(
        X_fit, y_fit,
        eval_set=[(X_val, y_val)],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(0)],
    )
    best_iteration = probe.best_iteration_ or MAX_ESTIMATORS

    X_train, y_train = train[feature_cols], train[target].astype(int)
    final_model = lgb.LGBMClassifier(n_estimators=best_iteration, **BASE_PARAMS)
    final_model.fit(X_train, y_train)

    X_test, y_test = test[feature_cols], test[target].astype(int)
    y_prob = final_model.predict_proba(X_test)[:, 1]

    return {
        "model": final_model,
        "best_iteration": int(best_iteration),
        "y_test": y_test.to_numpy(),
        "y_prob": y_prob,
        "n_fit": len(fit_df),
        "n_val": len(val_df),
        "n_train_final": len(train),
        "n_test": len(test),
    }


def train_lgbm_fixed(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target: str,
    feature_cols: list[str],
    n_estimators: int = 100,
) -> dict:
    """A direct fit with NO internal early-stopping validation split - for
    the ensemble pilot experiment's tiny sample, where carving out yet
    another validation slice would leave too little data to be meaningful.
    A small fixed tree count (default 100, well below Phase 2's typical
    best_iteration) is used instead of tuning, to avoid overfitting a model
    that has no validation signal to check itself against."""
    X_train, y_train = train[feature_cols], train[target].astype(int)
    model = lgb.LGBMClassifier(n_estimators=n_estimators, **BASE_PARAMS)
    model.fit(X_train, y_train)
    X_test, y_test = test[feature_cols], test[target].astype(int)
    y_prob = model.predict_proba(X_test)[:, 1]
    return {
        "model": model,
        "best_iteration": n_estimators,
        "y_test": y_test.to_numpy(),
        "y_prob": y_prob,
        "n_fit": len(train),
        "n_val": 0,
        "n_train_final": len(train),
        "n_test": len(test),
    }


def _safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    if len(y_true) == 0 or y_true.min() == y_true.max():
        return float("nan")
    return roc_auc_score(y_true, y_prob)


def score(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    reference_prob: float,
) -> dict:
    """Same metric set Phase 2 used, standalone (doesn't require the method
    name / target bookkeeping phase2.evaluate.score_baseline expects)."""
    y_pred = (y_prob >= threshold).astype(int)
    if len(y_true) == 0:
        return {k: float("nan") for k in [
            "n", "prevalence", "roc_auc", "pr_auc", "brier_score", "brier_skill_score",
            "precision", "recall", "f1", "false_alarm_rate", "miss_rate",
        ]} | {"n": 0}

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    far = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    miss_rate = fn / (fn + tp) if (fn + tp) > 0 else float("nan")

    bs_model = brier_score_loss(y_true, y_prob)
    bs_ref = brier_score_loss(y_true, np.full_like(y_prob, reference_prob, dtype=float))
    bss = 1.0 - bs_model / bs_ref if bs_ref > 0 else float("nan")

    return {
        "n": int(len(y_true)),
        "prevalence": float(np.mean(y_true)),
        "roc_auc": _safe_auc(y_true, y_prob),
        "pr_auc": average_precision_score(y_true, y_prob) if y_true.max() > 0 else float("nan"),
        "brier_score": bs_model,
        "brier_skill_score": bss,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "false_alarm_rate": far,
        "miss_rate": miss_rate,
    }


def historical_climatology_predict(
    train: pd.DataFrame, test: pd.DataFrame, target: str, group_cols: list[str]
) -> np.ndarray:
    """Train-only-fit climatology lookup, applied to `test`. Falls back to
    the train-period global rate for any group unseen in training."""
    lookup = train.groupby(group_cols, observed=True)[target].mean()
    fallback = float(train[target].mean())
    keys = pd.MultiIndex.from_frame(test[group_cols]) if len(group_cols) > 1 else test[group_cols[0]]
    pred = keys.map(lookup)
    return pd.Series(pred, index=test.index, dtype=float).fillna(fallback).to_numpy()
