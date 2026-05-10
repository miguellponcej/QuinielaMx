"""Backtesting metrics."""

from __future__ import annotations

import numpy as np


def multiclass_accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """Return accuracy."""

    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length.")
    return float(np.mean(np.array(y_true) == np.array(y_pred)))


def multiclass_log_loss(y_true: list[str], probabilities: np.ndarray, labels: list[str]) -> float:
    """Return multiclass log loss."""

    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    clipped = np.clip(probabilities, 1e-15, 1 - 1e-15)
    losses = [-np.log(clipped[row_idx, label_to_idx[label]]) for row_idx, label in enumerate(y_true)]
    return float(np.mean(losses))


def multiclass_brier_score(y_true: list[str], probabilities: np.ndarray, labels: list[str]) -> float:
    """Return one-vs-rest averaged Brier score."""

    total = 0.0
    for idx, label in enumerate(labels):
        binary = np.array([1 if item == label else 0 for item in y_true])
        total += float(np.mean((probabilities[:, idx] - binary) ** 2))
    return float(total / len(labels))
