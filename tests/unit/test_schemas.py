"""Tests for event schemas."""

import pytest
from pydantic import ValidationError

from producers.schemas import SensorReading, ActivityEvent, SensorType, EventType


class TestSensorReading:
    def test_valid_reading(self):
        r = SensorReading(
            device_id="sensor-001",
            sensor_type=SensorType.TEMPERATURE,
            value=22.5,
            unit="celsius",
            timestamp=1700000000000,
        )
        assert r.device_id == "sensor-001"
        assert r.sensor_type == SensorType.TEMPERATURE
        assert r.partition_key() == "sensor-001"

    def test_invalid_sensor_type(self):
        with pytest.raises(ValidationError):
            SensorReading(
                device_id="sensor-001",
                sensor_type="invalid",
                value=22.5,
                unit="celsius",
                timestamp=1700000000000,
            )

    def test_model_dump(self):
        r = SensorReading(
            device_id="sensor-001",
            sensor_type=SensorType.HUMIDITY,
            value=55.0,
            unit="percent",
            timestamp=1700000000000,
        )
        data = r.model_dump()
        assert data["device_id"] == "sensor-001"
        assert data["sensor_type"] == "humidity"


class TestActivityEvent:
    def test_valid_event(self):
        e = ActivityEvent(
            session_id="abc123",
            user_id="user-xyz",
            event_type=EventType.PAGE_VIEW,
            page="/products",
            timestamp=1700000000000,
        )
        assert e.value is None
        assert e.partition_key() == "user-xyz"

    def test_purchase_with_value(self):
        e = ActivityEvent(
            session_id="abc123",
            user_id="user-xyz",
            event_type=EventType.PURCHASE,
            page="/checkout",
            value=49.99,
            timestamp=1700000000000,
        )
        assert e.value == 49.99

    def test_invalid_event_type(self):
        with pytest.raises(ValidationError):
            ActivityEvent(
                session_id="abc123",
                user_id="user-xyz",
                event_type="invalid",
                page="/",
                timestamp=1700000000000,
            )
