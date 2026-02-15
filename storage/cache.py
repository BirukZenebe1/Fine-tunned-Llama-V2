"""Real-time metrics cache — latest values, alerts, and leaderboards in Redis."""

import json

from storage.redis_client import RedisClient


class MetricsCache:
    """
    Uses Redis hashes for O(1) latest-value lookups,
    bounded lists for alerts, and sorted sets for leaderboards.
    """

    LATEST_IOT_KEY = "metrics:iot:latest"
    LATEST_ACTIVITY_KEY = "metrics:activity:latest"
    ALERTS_KEY = "alerts:anomalies"
    LEADERBOARD_KEY = "rank:activity:purchases"
    MAX_ALERTS = 100

    def __init__(self, client: RedisClient):
        self._client = client

    # ─── Latest Values ──────────────────────────────────────────────

    def update_iot_latest(self, device_id: str, data: dict):
        def _op(r):
            r.hset(self.LATEST_IOT_KEY, device_id, json.dumps(data))
        self._client.execute_with_retry(_op)

    def update_activity_latest(self, event_type: str, data: dict):
        def _op(r):
            r.hset(self.LATEST_ACTIVITY_KEY, event_type, json.dumps(data))
        self._client.execute_with_retry(_op)

    def get_iot_latest(self) -> dict[str, dict]:
        def _op(r):
            raw = r.hgetall(self.LATEST_IOT_KEY)
            return {k: json.loads(v) for k, v in raw.items()}
        return self._client.execute_with_retry(_op)

    def get_activity_latest(self) -> dict[str, dict]:
        def _op(r):
            raw = r.hgetall(self.LATEST_ACTIVITY_KEY)
            return {k: json.loads(v) for k, v in raw.items()}
        return self._client.execute_with_retry(_op)

    # ─── Anomaly Alerts ─────────────────────────────────────────────

    def push_alert(self, alert_data: dict):
        def _op(r):
            pipe = r.pipeline()
            pipe.lpush(self.ALERTS_KEY, json.dumps(alert_data))
            pipe.ltrim(self.ALERTS_KEY, 0, self.MAX_ALERTS - 1)
            pipe.execute()
        self._client.execute_with_retry(_op)

    def get_alerts(self, limit: int = 50) -> list[dict]:
        def _op(r):
            raw = r.lrange(self.ALERTS_KEY, 0, limit - 1)
            return [json.loads(item) for item in raw]
        return self._client.execute_with_retry(_op)

    # ─── Leaderboards ───────────────────────────────────────────────

    def update_leaderboard(self, member: str, score: float):
        def _op(r):
            r.zincrby(self.LEADERBOARD_KEY, score, member)
        self._client.execute_with_retry(_op)

    def get_leaderboard(self, top_n: int = 10) -> list[dict]:
        def _op(r):
            raw = r.zrevrange(self.LEADERBOARD_KEY, 0, top_n - 1, withscores=True)
            return [{"page": member, "total_value": score} for member, score in raw]
        return self._client.execute_with_retry(_op)

    # ─── Dashboard Pub/Sub ──────────────────────────────────────────

    def publish_update(self, data: dict):
        def _op(r):
            r.publish("channel:dashboard_updates", json.dumps(data))
        self._client.execute_with_retry(_op)
