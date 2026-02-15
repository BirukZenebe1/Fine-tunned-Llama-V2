"""Linear regression trend analysis over sliding windows."""

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class TrendResult:
    key: str
    slope: float
    r_squared: float
    direction: str  # "rising" | "falling" | "stable"
    confidence: float  # 0.0 to 1.0
    data_points: int


class TrendAnalyzer:
    """
    Online OLS linear regression over a sliding window.

    Classifies each key's trend as rising, falling, or stable based on
    the slope's sign and statistical significance (R²).
    """

    MIN_POINTS = 20  # Need at least this many for meaningful regression

    def __init__(self, window_size: int = 60):
        self._windows: dict[str, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )

    def add(self, key: str, value: float, timestamp: float):
        self._windows[key].append((timestamp, value))

    def get_trend(self, key: str) -> TrendResult | None:
        window = self._windows.get(key)
        if window is None or len(window) < self.MIN_POINTS:
            return None

        n = len(window)
        xs = [t for t, _ in window]
        ys = [v for _, v in window]

        # Normalize timestamps to avoid floating-point issues
        x_min = xs[0]
        xs_norm = [x - x_min for x in xs]

        sum_x = sum(xs_norm)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs_norm, ys))
        sum_x2 = sum(x * x for x in xs_norm)
        sum_y2 = sum(y * y for y in ys)

        denom = n * sum_x2 - sum_x * sum_x
        if abs(denom) < 1e-10:
            return TrendResult(
                key=key, slope=0.0, r_squared=0.0,
                direction="stable", confidence=0.0, data_points=n,
            )

        slope = (n * sum_xy - sum_x * sum_y) / denom

        # R² (coefficient of determination)
        ss_tot = sum_y2 - (sum_y * sum_y) / n
        if abs(ss_tot) < 1e-10:
            r_squared = 0.0
        else:
            intercept = (sum_y - slope * sum_x) / n
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs_norm, ys))
            r_squared = max(0.0, 1.0 - ss_res / ss_tot)

        # Classify direction: slope must be significant AND R² must be meaningful
        if r_squared < 0.1:
            direction = "stable"
        elif slope > 0.001:
            direction = "rising"
        elif slope < -0.001:
            direction = "falling"
        else:
            direction = "stable"

        return TrendResult(
            key=key,
            slope=round(slope, 6),
            r_squared=round(r_squared, 4),
            direction=direction,
            confidence=round(r_squared, 4),
            data_points=n,
        )

    def get_all_trends(self) -> list[TrendResult]:
        results = []
        for key in self._windows:
            result = self.get_trend(key)
            if result:
                results.append(result)
        return results
