"""Probability calibration helpers."""

from __future__ import annotations

import numpy as np


class BinaryCalibrator:
    """Simple monotonic bin calibrator for one-vs-rest probabilities."""

    def __init__(self) -> None:
        self.bin_edges: np.ndarray | None = None
        self.bin_values: np.ndarray | None = None
        self.is_fitted = False

    def fit(self, predicted: np.ndarray, actual: np.ndarray) -> "BinaryCalibrator":
        """Fit calibrator."""

        predicted = np.asarray(predicted, dtype=float)
        actual = np.asarray(actual, dtype=float)
        self.bin_edges = np.linspace(0, 1, 11)
        values = []
        for left, right in zip(self.bin_edges[:-1], self.bin_edges[1:], strict=True):
            mask = (predicted >= left) & (predicted <= right)
            values.append(float(actual[mask].mean()) if mask.any() else (left + right) / 2)
        self.bin_values = np.maximum.accumulate(np.asarray(values, dtype=float))
        self.is_fitted = True
        return self

    def predict(self, predicted: np.ndarray) -> np.ndarray:
        """Calibrate probabilities."""

        if not self.is_fitted or self.bin_edges is None or self.bin_values is None:
            return predicted
        indexes = np.clip(np.digitize(predicted, self.bin_edges) - 1, 0, len(self.bin_values) - 1)
        return self.bin_values[indexes]
