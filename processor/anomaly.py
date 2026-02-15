"""Rolling z-score anomaly detection with adaptive thresholds."""

import statistics
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class AnomalyEvent:
    key: str
    value: float
    z_score: float
    mean: float
    std: float
    threshold: float
    severity: str  # "warning" | "critical"
    timestamp: float


class ZScoreDetector:
    """
    Rolling z-score anomaly detector.

    Maintains a window of recent values per key. For each new value, computes:
        z = (value - rolling_mean) / rolling_std

    If |z| > threshold, an AnomalyEvent is emitted.
    Severity: |z| > 4.0 → critical, else → warning.
    """

    MIN_WINDOW_SIZE = 10  # Need at least this many points before detecting

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self._windows: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._threshold = z_threshold

    def check(self, key: str, value: float, timestamp: float) -> AnomalyEvent | None:
        """
        Add value to rolling window. Returns AnomalyEvent if anomalous, else None.
        Requires at least MIN_WINDOW_SIZE points before detection begins.
        """
        window = self._windows[key]
        window.append(value)

        if len(window) < self.MIN_WINDOW_SIZE:
            return None

        mean = statistics.mean(window)
        std = statistics.stdev(window)

        if std < 1e-10:
            return None

        z_score = (value - mean) / std

        if abs(z_score) > self._threshold:
            return AnomalyEvent(
                key=key,
                value=value,
                z_score=round(z_score, 3),
                mean=round(mean, 3),
                std=round(std, 3),
                threshold=self._threshold,
                severity="critical" if abs(z_score) > 4.0 else "warning",
                timestamp=timestamp,
            )
        return None

    @property
    def tracked_keys(self) -> list[str]:
        return list(self._windows.keys())
