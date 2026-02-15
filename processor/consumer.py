"""Kafka consumer with manual offset commits and graceful shutdown."""

import signal
import time
from typing import Callable

import msgpack
from kafka import KafkaConsumer

from config import Settings, configure_logging
from processor.dead_letter import DeadLetterQueue


class StreamConsumer:
    """
    Kafka consumer that polls batches, deserializes with MessagePack,
    routes each message to a handler, and commits offsets manually.
    Unprocessable messages are sent to the dead letter queue.
    """

    def __init__(self, settings: Settings, handler: Callable[[str, str | None, dict], None]):
        self.settings = settings
        self.log = configure_logging("consumer", settings.log_level)
        self._handler = handler
        self._running = True
        self._dlq = DeadLetterQueue(settings)
        self._processed = 0
        self._errors = 0

        self._consumer = KafkaConsumer(
            settings.topic_iot_raw,
            settings.topic_activity_raw,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=False,
            value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
            max_poll_records=settings.kafka_max_poll_records,
            session_timeout_ms=settings.kafka_session_timeout_ms,
        )

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        self.log.info(
            "consumer_started",
            topics=[settings.topic_iot_raw, settings.topic_activity_raw],
            group=settings.kafka_consumer_group,
        )

    def run(self):
        """Main consumption loop with batch processing and manual commits."""
        try:
            while self._running:
                batch = self._consumer.poll(timeout_ms=1000)
                if not batch:
                    continue

                for tp, messages in batch.items():
                    for msg in messages:
                        try:
                            key = msg.key.decode("utf-8") if msg.key else None
                            self._handler(msg.topic, key, msg.value)
                            self._processed += 1
                        except Exception as e:
                            self._errors += 1
                            self.log.error(
                                "message_processing_error",
                                topic=msg.topic,
                                partition=msg.partition,
                                offset=msg.offset,
                                error=str(e),
                            )
                            self._dlq.send(
                                original_value=msg.value if isinstance(msg.value, bytes) else None,
                                error=e,
                                source_topic=msg.topic,
                                source_partition=msg.partition,
                                source_offset=msg.offset,
                            )

                # Commit after processing the entire batch
                self._commit()

                if self._processed % 5000 == 0 and self._processed > 0:
                    self.log.info(
                        "consumer_progress",
                        processed=self._processed,
                        errors=self._errors,
                    )
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def _commit(self):
        try:
            self._consumer.commit()
        except Exception as e:
            self.log.error("commit_error", error=str(e))

    def _shutdown(self, signum, frame):
        self.log.info("shutdown_signal", signal=signum)
        self._running = False

    def _cleanup(self):
        self.log.info("consumer_closing", processed=self._processed, errors=self._errors)
        self._consumer.close()
        self._dlq.close()
