"""Tests for linear regression trend analysis."""

import pytest

from processor.trend import TrendAnalyzer


class TestTrendAnalyzer:
    def test_insufficient_data_returns_none(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(10):
            analyzer.add("key", float(i), 1000.0 + i)
        assert analyzer.get_trend("key") is None

    def test_unknown_key_returns_none(self):
        analyzer = TrendAnalyzer()
        assert analyzer.get_trend("nonexistent") is None

    def test_rising_trend(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(30):
            analyzer.add("key", float(i) * 2.0, 1000.0 + i)
        result = analyzer.get_trend("key")
        assert result is not None
        assert result.direction == "rising"
        assert result.slope > 0
        assert result.r_squared > 0.9

    def test_falling_trend(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(30):
            analyzer.add("key", 100.0 - float(i) * 2.0, 1000.0 + i)
        result = analyzer.get_trend("key")
        assert result is not None
        assert result.direction == "falling"
        assert result.slope < 0

    def test_stable_trend(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(30):
            analyzer.add("key", 42.0, 1000.0 + i)
        result = analyzer.get_trend("key")
        assert result is not None
        assert result.direction == "stable"

    def test_get_all_trends(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(25):
            analyzer.add("up", float(i), 1000.0 + i)
            analyzer.add("down", 50.0 - float(i), 1000.0 + i)
        results = analyzer.get_all_trends()
        assert len(results) == 2
        dirs = {r.key: r.direction for r in results}
        assert dirs["up"] == "rising"
        assert dirs["down"] == "falling"

    def test_data_points_count(self):
        analyzer = TrendAnalyzer(window_size=60)
        for i in range(25):
            analyzer.add("key", float(i), 1000.0 + i)
        result = analyzer.get_trend("key")
        assert result.data_points == 25
