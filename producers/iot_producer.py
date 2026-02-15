"""IoT sensor data producer — simulates temperature, humidity, and pressure devices."""

import random
import time
from dataclasses import dataclass, field

from config import Settings
from producers.base_producer import BaseProducer
from producers.noise import NoiseGenerator
from producers.schemas import SensorReading, SensorType


@dataclass
class DeviceState:
    device_id: str
    sensor_type: SensorType
    unit: str
    baseline: float
    noise_std: float
    location: str
    _start_time: float = field(default_factory=time.time)

    def simulate_value(self) -> float:
        elapsed = time.time() - self._start_time
        value = self.baseline
        value += NoiseGenerator.sinusoidal(elapsed, period=300, amplitude=2.0)
        value += NoiseGenerator.gaussian(0, self.noise_std)
        value += NoiseGenerator.spike(probability=0.005, magnitude=self.noise_std * 5)
        value += NoiseGenerator.drift(elapsed, rate=0.0005)
        return round(value, 2)


SENSOR_PROFILES = [
    {"sensor_type": SensorType.TEMPERATURE, "unit": "celsius", "baseline": 22.0, "noise_std": 0.5},
    {"sensor_type": SensorType.HUMIDITY, "unit": "percent", "baseline": 55.0, "noise_std": 2.0},
    {"sensor_type": SensorType.PRESSURE, "unit": "hPa", "baseline": 1013.25, "noise_std": 1.0},
]

LOCATIONS = ["datacenter-1", "datacenter-2", "warehouse-a", "warehouse-b", "office-hq"]


class IoTProducer(BaseProducer):
    def __init__(self, settings: Settings):
        super().__init__(settings, "iot-producer")
        self.devices = self._init_devices(settings.iot_num_devices)
        self._interval = settings.iot_publish_interval_ms / 1000.0
        self.log.info("devices_initialized", count=len(self.devices))

    def _init_devices(self, count: int) -> list[DeviceState]:
        devices = []
        for i in range(count):
            profile = SENSOR_PROFILES[i % len(SENSOR_PROFILES)]
            devices.append(
                DeviceState(
                    device_id=f"sensor-{i:03d}",
                    sensor_type=profile["sensor_type"],
                    unit=profile["unit"],
                    baseline=profile["baseline"],
                    noise_std=profile["noise_std"],
                    location=random.choice(LOCATIONS),
                )
            )
        return devices

    def generate_event(self) -> tuple[str, str, dict]:
        device = random.choice(self.devices)
        reading = SensorReading(
            device_id=device.device_id,
            sensor_type=device.sensor_type,
            value=device.simulate_value(),
            unit=device.unit,
            timestamp=time.time() * 1000,
            location=device.location,
        )
        return (self.settings.topic_iot_raw, reading.partition_key(), reading.model_dump())

    def get_interval(self) -> float:
        # Add small jitter to avoid synchronized bursts
        return self._interval * (0.8 + random.random() * 0.4)


if __name__ == "__main__":
    settings = Settings()
    producer = IoTProducer(settings)
    producer.run()
