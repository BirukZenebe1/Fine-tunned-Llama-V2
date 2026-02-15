"""Tests for z-score anomaly detection."""

import pytest

from processor.anomaly import ZScoreDetector


class TestZScoreDetector:
    def test_no_anomaly_with_few_points(self):
        detector = ZScoreDetector(window_size=100, z_threshold=3.0)
        # Less than MIN_WINDOW_SIZE points should return None
        for i in range(9):
            result = detector.check("key", float(i), 1000.0 + i)
            assert result is None

    def test_no_anomaly_with_stable_data(self):
        detector = ZScoreDetector(window_size=100, z_threshold=3.0)
        # Feed stable values — no anomaly expected
        for i in range(50):
            result = detector.check("key", 20.0 + (i % 2) * 0.1, 1000.0 + i)
        assert result is None

    def test_detects_spike(self):
        detector = ZScoreDetector(window_size=50, z_threshold=3.0)
        # Build baseline of stable values
        for i in range(40):
            detector.check("key", 20.0, 1000.0 + i)
        # Inject a massive spike
        result = detector.check("key", 100.0, 1050.0)
        assert result is not None
        assert result.severity in ("warning", "critical")
        assert result.z_score > 3.0

    def test_critical_severity(self):
        detector = ZScoreDetector(window_size=50, z_threshold=3.0)
        for i in range(40):
            detector.check("key", 20.0, 1000.0 + i)
        # Very large spike should be critical
        result = detector.check("key", 200.0, 1050.0)
        assert result is not None
        assert result.severity == "critical"
        assert abs(result.z_score) > 4.0

    def test_multiple_keys_independent(self):
        detector = ZScoreDetector(window_size=50, z_threshold=3.0)
        for i in range(40):
            detector.check("stable", 20.0, 1000.0 + i)
            detector.check("volatile", 20.0 + i * 10, 1000.0 + i)
        # Spike on stable key should detect anomaly
        result = detector.check("stable", 100.0, 1050.0)
        assert result is not None

    def test_zero_std_returns_none(self):
        detector = ZScoreDetector(window_size=50, z_threshold=3.0)
        # All identical values → std = 0 → no anomaly possible
        for i in range(20):
            result = detector.check("key", 42.0, 1000.0 + i)
        assert result is None

    def test_tracked_keys(self):
        detector = ZScoreDetector()
        detector.check("a", 1.0, 1000.0)
        detector.check("b", 2.0, 1001.0)
        assert set(detector.tracked_keys) == {"a", "b"}
