"""Shared test fixtures."""

import pytest

from config import Settings


@pytest.fixture
def settings():
    """Test settings with localhost defaults."""
    return Settings(
        kafka_bootstrap_servers="localhost:9092",
        redis_url="redis://localhost:6379/1",
    )
