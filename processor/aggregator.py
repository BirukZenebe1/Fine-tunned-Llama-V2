"""Windowed aggregation engine — tumbling and sliding windows with statistical metrics."""

from collections import deque
from dataclasses import dataclass, field
import time


@dataclass
class AggregateResult:
    key: str
    window_start: float
    window_end: float
    count: int
    total: float
    avg: float
    min_val: float
    max_val: float
    p99: float


class TumblingWindow:
    """Accumulates values for a fixed, non-overlapping time interval."""

    __slots__ = ("values", "start_time")

    def __init__(self):
        self.values: list[float] = []
        self.start_time: float = time.time()

    def add(self, value: float):
        self.values.append(value)

    def compute(self, key: str) -> AggregateResult | None:
        if not self.values:
            return None
        sorted_vals = sorted(self.values)
        count = len(sorted_vals)
        p99_idx = max(0, int(count * 0.99) - 1)
        now = time.time()
        return AggregateResult(
            key=key,
            window_start=self.start_time,
            window_end=now,
            count=count,
            total=sum(sorted_vals),
            avg=sum(sorted_vals) / count,
            min_val=sorted_vals[0],
            max_val=sorted_vals[-1],
            p99=sorted_vals[p99_idx],
        )

    def reset(self):
        self.values.clear()
        self.start_time = time.time()


class SlidingWindow:
    """Time-bounded deque of (timestamp, value) pairs with automatic eviction."""

    __slots__ = ("entries", "window_sec")

    def __init__(self, window_sec: float):
        self.entries: deque[tuple[float, float]] = deque()
        self.window_sec = window_sec

    def add(self, value: float, timestamp: float):
        self.entries.append((timestamp, value))
        self._evict(timestamp)

    def _evict(self, now: float):
        cutoff = now - self.window_sec
        while self.entries and self.entries[0][0] < cutoff:
            self.entries.popleft()

    def compute(self, key: str) -> AggregateResult | None:
        now = time.time()
        self._evict(now)
        if not self.entries:
            return None
        values = [v for _, v in self.entries]
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        p99_idx = max(0, int(count * 0.99) - 1)
        return AggregateResult(
            key=key,
            window_start=self.entries[0][0],
            window_end=now,
            count=count,
            total=sum(sorted_vals),
            avg=sum(sorted_vals) / count,
            min_val=sorted_vals[0],
            max_val=sorted_vals[-1],
            p99=sorted_vals[p99_idx],
        )


class WindowedAggregator:
    """
    Maintains both tumbling and sliding window aggregations per key.

    Tumbling: Fixed 10s windows, flushed periodically. Emits final aggregates.
    Sliding:  60s rolling window, queryable at any time.
    """

    def __init__(self, tumbling_sec: int = 10, sliding_sec: int = 60):
        self.tumbling_sec = tumbling_sec
        self.sliding_sec = sliding_sec
        self._tumbling: dict[str, TumblingWindow] = {}
        self._sliding: dict[str, SlidingWindow] = {}

    def add(self, key: str, value: float, timestamp: float):
        """Add a data point to both window types."""
        if key not in self._tumbling:
            self._tumbling[key] = TumblingWindow()
        if key not in self._sliding:
            self._sliding[key] = SlidingWindow(self.sliding_sec)

        self._tumbling[key].add(value)
        self._sliding[key].add(value, timestamp)

    def flush_tumbling(self) -> list[AggregateResult]:
        """Flush all tumbling windows and return aggregate results."""
        results = []
        for key, window in self._tumbling.items():
            result = window.compute(key)
            if result:
                results.append(result)
            window.reset()
        return results

    def query_sliding(self, key: str) -> AggregateResult | None:
        """Query the current sliding window for a specific key."""
        window = self._sliding.get(key)
        if window is None:
            return None
        return window.compute(key)

    def get_all_sliding(self) -> list[AggregateResult]:
        """Query all sliding windows."""
        results = []
        for key, window in self._sliding.items():
            result = window.compute(key)
            if result:
                results.append(result)
        return results

    @property
    def active_keys(self) -> list[str]:
        return list(self._tumbling.keys())
