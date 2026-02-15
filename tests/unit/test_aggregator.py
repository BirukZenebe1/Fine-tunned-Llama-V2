"""Tests for the windowed aggregation engine."""

import time
import pytest

from processor.aggregator import WindowedAggregator, TumblingWindow, SlidingWindow


class TestTumblingWindow:
    def test_empty_compute_returns_none(self):
        w = TumblingWindow()
        assert w.compute("key") is None

    def test_single_value(self):
        w = TumblingWindow()
        w.add(42.0)
        result = w.compute("test")
        assert result is not None
        assert result.count == 1
        assert result.avg == 42.0
        assert result.min_val == 42.0
        assert result.max_val == 42.0

    def test_multiple_values(self):
        w = TumblingWindow()
        for v in [10, 20, 30, 40, 50]:
            w.add(v)
        result = w.compute("test")
        assert result.count == 5
        assert result.avg == 30.0
        assert result.min_val == 10.0
        assert result.max_val == 50.0
        assert result.total == 150.0

    def test_p99(self):
        w = TumblingWindow()
        for v in range(1, 101):
            w.add(float(v))
        result = w.compute("test")
        assert result.p99 == 99.0

    def test_reset(self):
        w = TumblingWindow()
        w.add(1.0)
        w.reset()
        assert w.compute("test") is None


class TestSlidingWindow:
    def test_empty_compute_returns_none(self):
        w = SlidingWindow(window_sec=60)
        assert w.compute("key") is None

    def test_eviction(self):
        w = SlidingWindow(window_sec=10)
        now = time.time()
        # Add old entry
        w.add(1.0, now - 15)
        # Add current entry
        w.add(2.0, now)
        result = w.compute("test")
        assert result is not None
        assert result.count == 1
        assert result.avg == 2.0

    def test_within_window(self):
        w = SlidingWindow(window_sec=60)
        now = time.time()
        for i in range(10):
            w.add(float(i), now - i)
        result = w.compute("test")
        assert result.count == 10


class TestWindowedAggregator:
    def test_add_and_flush(self):
        agg = WindowedAggregator(tumbling_sec=10, sliding_sec=60)
        now = time.time()
        agg.add("key1", 10.0, now)
        agg.add("key1", 20.0, now + 1)
        agg.add("key2", 5.0, now)

        results = agg.flush_tumbling()
        assert len(results) == 2

        key1_result = next(r for r in results if r.key == "key1")
        assert key1_result.count == 2
        assert key1_result.avg == 15.0

    def test_flush_resets_tumbling(self):
        agg = WindowedAggregator()
        agg.add("key1", 10.0, time.time())
        agg.flush_tumbling()
        results = agg.flush_tumbling()
        # After reset, key1's tumbling window should be empty
        key1_results = [r for r in results if r.key == "key1"]
        assert len(key1_results) == 0

    def test_sliding_persists_after_flush(self):
        agg = WindowedAggregator(sliding_sec=60)
        now = time.time()
        agg.add("key1", 10.0, now)
        agg.flush_tumbling()
        sliding = agg.query_sliding("key1")
        assert sliding is not None
        assert sliding.count == 1

    def test_active_keys(self):
        agg = WindowedAggregator()
        agg.add("a", 1.0, time.time())
        agg.add("b", 2.0, time.time())
        assert set(agg.active_keys) == {"a", "b"}
