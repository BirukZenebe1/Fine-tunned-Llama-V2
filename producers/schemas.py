"""Canonical event schemas — single source of truth for data shapes across the pipeline."""

from enum import Enum

from pydantic import BaseModel, Field


class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"


class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    CLICK = "click"
    PURCHASE = "purchase"


class SensorReading(BaseModel):
    device_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float = Field(description="Unix epoch in milliseconds")
    location: str = "datacenter-1"

    def partition_key(self) -> str:
        return self.device_id


class ActivityEvent(BaseModel):
    session_id: str
    user_id: str
    event_type: EventType
    page: str
    value: float | None = None  # Purchase amount for purchase events
    timestamp: float = Field(description="Unix epoch in milliseconds")

    def partition_key(self) -> str:
        return self.user_id
