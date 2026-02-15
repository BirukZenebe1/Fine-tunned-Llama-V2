"""Stream processor — orchestrates consumer, aggregator, anomaly detection, and trend analysis."""

import threading
import time
from dataclasses import asdict

from config import Settings, configure_logging
from processor.aggregator import WindowedAggregator
from processor.anomaly import ZScoreDetector
from processor.consumer import StreamConsumer
from processor.trend import TrendAnalyzer
from storage.redis_client import RedisClient
from storage.time_series import TimeSeriesWriter
from storage.cache import MetricsCache


class StreamProcessor:
    """
    Wires together: Kafka Consumer → Aggregator + Anomaly + Trend → Redis.
    Runs a periodic flush timer for tumbling window aggregates.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.log = configure_logging("stream-processor", settings.log_level)

        # Processing components
        self._aggregator = WindowedAggregator(
            tumbling_sec=settings.tumbling_window_sec,
            sliding_sec=settings.sliding_window_sec,
        )
        self._anomaly = ZScoreDetector(
            window_size=settings.anomaly_window_size,
            z_threshold=settings.anomaly_z_threshold,
        )
        self._trend = TrendAnalyzer(window_size=60)

        # Storage
        self._redis = RedisClient(settings)
        self._ts_writer = TimeSeriesWriter(
            self._redis,
            pipeline_batch=settings.redis_pipeline_batch,
            retention_ms=settings.redis_ts_retention_ms,
        )
        self._cache = MetricsCache(self._redis)

        # Consumer
        self._consumer = StreamConsumer(settings, handler=self.process_message)

        # Flush timer
        self._flush_running = True
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True
        )

    def process_message(self, topic: str, key: str | None, value: dict):
        """Route a message to the appropriate processing pipeline."""
        if topic == self.settings.topic_iot_raw:
            self._process_iot(value)
        elif topic == self.settings.topic_activity_raw:
            self._process_activity(value)

    def _process_iot(self, event: dict):
        device_id = event["device_id"]
        sensor_type = event["sensor_type"]
        val = event["value"]
        ts = event["timestamp"]
        agg_key = f"iot:{sensor_type}:{device_id}"

        # Feed into aggregator
        self._aggregator.add(agg_key, val, ts)

        # Check for anomalies
        anomaly = self._anomaly.check(agg_key, val, ts)
        if anomaly:
            alert = asdict(anomaly)
            self._cache.push_alert(alert)
            self.log.warning("anomaly_detected", **alert)

        # Feed trend analyzer
        self._trend.add(agg_key, val, ts)

        # Write raw time-series data
        self._ts_writer.write(agg_key, ts, event)

        # Update latest cache
        self._cache.update_iot_latest(device_id, event)

    def _process_activity(self, event: dict):
        event_type = event["event_type"]
        ts = event["timestamp"]
        agg_key = f"activity:{event_type}"

        # Count-based aggregation (value = 1 per event)
        self._aggregator.add(agg_key, 1.0, ts)

        # Track purchases in leaderboard
        if event_type == "purchase" and event.get("value"):
            self._cache.update_leaderboard(event["page"], event["value"])

        # Write raw time-series
        self._ts_writer.write(agg_key, ts, event)

        # Update latest cache
        self._cache.update_activity_latest(event_type, {
            "event_type": event_type,
            "count": self._aggregator.query_sliding(agg_key).count
            if self._aggregator.query_sliding(agg_key)
            else 0,
            "timestamp": ts,
        })

    def _flush_loop(self):
        """Periodically flush tumbling windows and publish dashboard updates."""
        while self._flush_running:
            time.sleep(self.settings.tumbling_window_sec)
            try:
                self._flush_windows()
            except Exception as e:
                self.log.error("flush_error", error=str(e))

    def _flush_windows(self):
        """Flush tumbling windows, compute trends, and publish to dashboard."""
        tumbling_results = self._aggregator.flush_tumbling()
        sliding_results = self._aggregator.get_all_sliding()
        trends = self._trend.get_all_trends()

        # Flush any remaining buffered time-series writes
        self._ts_writer.flush()

        # Build dashboard update payload
        dashboard_update = {
            "type": "window_flush",
            "timestamp": time.time() * 1000,
            "tumbling": [
                {
                    "key": r.key,
                    "count": r.count,
                    "avg": round(r.avg, 3),
                    "min": round(r.min_val, 3),
                    "max": round(r.max_val, 3),
                    "p99": round(r.p99, 3),
                }
                for r in tumbling_results
            ],
            "sliding": [
                {
                    "key": r.key,
                    "count": r.count,
                    "avg": round(r.avg, 3),
                    "min": round(r.min_val, 3),
                    "max": round(r.max_val, 3),
                }
                for r in sliding_results
            ],
            "trends": [
                {
                    "key": t.key,
                    "direction": t.direction,
                    "slope": t.slope,
                    "confidence": t.confidence,
                }
                for t in trends
            ],
        }

        # Publish to Redis Pub/Sub for WebSocket broadcast
        self._cache.publish_update(dashboard_update)

        self.log.info(
            "windows_flushed",
            tumbling_keys=len(tumbling_results),
            sliding_keys=len(sliding_results),
            trends=len(trends),
        )

    def run(self):
        """Start the processor: flush thread + consumer loop."""
        self.log.info("stream_processor_starting")
        self._flush_thread.start()
        try:
            self._consumer.run()
        finally:
            self._flush_running = False
            self._ts_writer.flush()
            self._redis.close()
            self.log.info("stream_processor_stopped")


if __name__ == "__main__":
    settings = Settings()
    processor = StreamProcessor(settings)
    processor.run()
