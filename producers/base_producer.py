"""Abstract base Kafka producer with batching, compression, and graceful shutdown."""

import signal
import sys
import time
from abc import ABC, abstractmethod

import msgpack
from kafka import KafkaProducer
from kafka.errors import KafkaError

from config import Settings, configure_logging


class BaseProducer(ABC):
    def __init__(self, settings: Settings, component_name: str = "producer"):
        self.settings = settings
        self.log = configure_logging(component_name, settings.log_level)
        self._running = True
        self._sent_count = 0
        self._error_count = 0
        self._producer: KafkaProducer | None = None

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _connect(self) -> KafkaProducer:
        """Create Kafka producer with optimized settings."""
        self.log.info(
            "connecting_to_kafka",
            servers=self.settings.kafka_bootstrap_servers,
        )
        return KafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: msgpack.packb(v, use_bin_type=True),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            batch_size=self.settings.kafka_producer_batch_size,
            linger_ms=self.settings.kafka_producer_linger_ms,
            compression_type=self.settings.kafka_producer_compression,
            acks="all",
            retries=3,
            retry_backoff_ms=200,
            buffer_memory=67108864,  # 64MB
        )

    @abstractmethod
    def generate_event(self) -> tuple[str, str, dict]:
        """Return (topic, partition_key, event_dict). Subclasses implement."""

    @abstractmethod
    def get_interval(self) -> float:
        """Return sleep interval between events in seconds."""

    def run(self):
        """Main production loop."""
        self._producer = self._connect()
        self.log.info("producer_started")

        try:
            while self._running:
                topic, key, value = self.generate_event()
                self._producer.send(
                    topic,
                    key=key,
                    value=value,
                ).add_callback(self._on_success).add_errback(self._on_error)

                time.sleep(self.get_interval())
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def _on_success(self, metadata):
        self._sent_count += 1
        if self._sent_count % 1000 == 0:
            self.log.info(
                "producer_progress",
                sent=self._sent_count,
                errors=self._error_count,
            )

    def _on_error(self, exc: KafkaError):
        self._error_count += 1
        self.log.error("produce_error", error=str(exc))

    def _shutdown(self, signum, frame):
        self.log.info("shutdown_signal_received", signal=signum)
        self._running = False

    def _cleanup(self):
        if self._producer:
            self.log.info("flushing_producer", pending="remaining messages")
            self._producer.flush(timeout=10)
            self._producer.close(timeout=10)
        self.log.info(
            "producer_stopped",
            total_sent=self._sent_count,
            total_errors=self._error_count,
        )
