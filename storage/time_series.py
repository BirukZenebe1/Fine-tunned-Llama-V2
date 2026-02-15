"""Time-series storage using Redis sorted sets."""

import json

from storage.redis_client import RedisClient


class TimeSeriesWriter:
    """
    Stores time-series data in Redis sorted sets (score = timestamp).
    Batches writes via Redis pipelining for throughput.
    Automatically trims old entries beyond retention period.
    """

    def __init__(self, client: RedisClient, pipeline_batch: int = 50, retention_ms: int = 86_400_000):
        self._client = client
        self._batch_size = pipeline_batch
        self._retention_ms = retention_ms
        self._pending: list[tuple[str, float, dict]] = []

    def write(self, key: str, timestamp: float, data: dict):
        """Buffer a write. Automatically flushes when batch is full."""
        self._pending.append((key, timestamp, data))
        if len(self._pending) >= self._batch_size:
            self.flush()

    def flush(self):
        """Execute all pending writes in a single Redis pipeline."""
        if not self._pending:
            return

        pipe = self._client.pipeline()
        now_ms = 0.0
        for key, timestamp, data in self._pending:
            ts_key = f"ts:{key}"
            payload = json.dumps(data)
            pipe.zadd(ts_key, {payload: timestamp})
            now_ms = max(now_ms, timestamp)

        # Trim entries older than retention period
        cutoff = now_ms - self._retention_ms
        trimmed_keys = set()
        for key, _, _ in self._pending:
            ts_key = f"ts:{key}"
            if ts_key not in trimmed_keys:
                pipe.zremrangebyscore(ts_key, "-inf", cutoff)
                trimmed_keys.add(ts_key)

        pipe.execute()
        self._pending.clear()


class TimeSeriesReader:
    """Read-side queries for time-series data stored in Redis sorted sets."""

    def __init__(self, client: RedisClient):
        self._client = client

    def get_range(self, key: str, start: float, end: float, max_points: int = 500) -> list[dict]:
        """Query time-series data within a time range."""
        ts_key = f"ts:{key}"

        def _query(r):
            raw = r.zrangebyscore(ts_key, start, end, withscores=True)
            results = []
            for payload, score in raw:
                data = json.loads(payload)
                data["_timestamp"] = score
                results.append(data)
            # Downsample if too many points
            if len(results) > max_points:
                step = len(results) // max_points
                results = results[::step]
            return results

        return self._client.execute_with_retry(_query)

    def get_latest(self, key: str) -> dict | None:
        """Get the most recent entry for a key."""
        ts_key = f"ts:{key}"

        def _query(r):
            raw = r.zrevrange(ts_key, 0, 0, withscores=True)
            if not raw:
                return None
            payload, score = raw[0]
            data = json.loads(payload)
            data["_timestamp"] = score
            return data

        return self._client.execute_with_retry(_query)

    def get_key_count(self, pattern: str = "ts:*") -> int:
        """Count time-series keys matching a pattern."""
        def _query(r):
            return len(list(r.scan_iter(match=pattern, count=100)))
        return self._client.execute_with_retry(_query)
