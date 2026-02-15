"""Dead letter queue — routes unprocessable messages to a DLQ topic with error context."""

import json
import time
import traceback

from kafka import KafkaProducer

from config import Settings, configure_logging


class DeadLetterQueue:
    def __init__(self, settings: Settings):
        self.log = configure_logging("dlq", settings.log_level)
        self._topic = settings.topic_dlq
        self._producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def send(
        self,
        original_value: bytes | None,
        error: Exception,
        source_topic: str,
        source_partition: int = -1,
        source_offset: int = -1,
    ):
        """Wrap the original message with error context and send to DLQ."""
        envelope = {
            "original_topic": source_topic,
            "original_partition": source_partition,
            "original_offset": source_offset,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "failed_at": time.time() * 1000,
            "original_value_b64": original_value.hex() if original_value else None,
        }
        self._producer.send(self._topic, value=envelope)
        self.log.warning(
            "message_sent_to_dlq",
            source_topic=source_topic,
            error_type=type(error).__name__,
        )

    def close(self):
        self._producer.flush(timeout=5)
        self._producer.close(timeout=5)
