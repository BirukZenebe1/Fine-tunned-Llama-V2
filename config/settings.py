"""Centralized configuration using pydantic-settings. All values are env-configurable."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PIPELINE_")

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_producer_batch_size: int = 16384
    kafka_producer_linger_ms: int = 50
    kafka_producer_compression: str = "lz4"
    kafka_consumer_group: str = "stream-processor"
    kafka_auto_offset_reset: str = "latest"
    kafka_max_poll_records: int = 500
    kafka_session_timeout_ms: int = 30000

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_pool_size: int = 20
    redis_pipeline_batch: int = 50
    redis_ts_retention_ms: int = 86_400_000  # 24 hours

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    ws_throttle_ms: int = 100

    # Processing
    tumbling_window_sec: int = 10
    sliding_window_sec: int = 60
    anomaly_z_threshold: float = 3.0
    anomaly_window_size: int = 100

    # Producers
    iot_num_devices: int = 10
    iot_publish_interval_ms: int = 200
    activity_events_per_sec: int = 50

    # Topics
    topic_iot_raw: str = "iot.sensors.raw"
    topic_activity_raw: str = "activity.events.raw"
    topic_dlq: str = "pipeline.dlq"

    # Monitoring
    enable_prometheus: bool = True
    log_level: str = "INFO"
