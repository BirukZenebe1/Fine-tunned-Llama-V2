"""Noise generators for realistic sensor simulation."""

import math
import random


class NoiseGenerator:
    @staticmethod
    def sinusoidal(t: float, period: float = 86400, amplitude: float = 1.0) -> float:
        """Sinusoidal signal (e.g. daily temperature cycle). t in seconds."""
        return amplitude * math.sin(2 * math.pi * t / period)

    @staticmethod
    def gaussian(mean: float = 0.0, std: float = 1.0) -> float:
        """Gaussian random noise."""
        return random.gauss(mean, std)

    @staticmethod
    def spike(probability: float = 0.005, magnitude: float = 15.0) -> float:
        """Occasional spike for anomaly detection to catch."""
        if random.random() < probability:
            return magnitude * random.choice([-1, 1])
        return 0.0

    @staticmethod
    def drift(t: float, rate: float = 0.001) -> float:
        """Gradual drift over time for trend analysis."""
        return rate * t
