"""Resilient Redis client with connection pooling and circuit breaker."""

import time
from typing import Any, Callable

import redis

from config import Settings, configure_logging


class CircuitBreaker:
    """
    Three-state circuit breaker: CLOSED → OPEN → HALF_OPEN.

    CLOSED: Normal operation. Track consecutive failures.
    OPEN:   After failure_threshold failures, reject all calls immediately.
    HALF_OPEN: After recovery_timeout, allow one test call through.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = 0.0

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        # half_open: allow one test call
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class CircuitOpenError(Exception):
    pass


class RedisClient:
    """Redis client wrapper with connection pooling, circuit breaker, and retry logic."""

    def __init__(self, settings: Settings):
        self.log = configure_logging("redis-client", settings.log_level)
        self._pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True,
        )
        self._circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        self.log.info("redis_pool_created", url=settings.redis_url, pool_size=settings.redis_pool_size)

    def get_client(self) -> redis.Redis:
        return redis.Redis(connection_pool=self._pool)

    def pipeline(self) -> redis.client.Pipeline:
        return self.get_client().pipeline()

    def execute_with_retry(
        self, func: Callable[[redis.Redis], Any], max_retries: int = 3
    ) -> Any:
        """Execute a Redis operation with circuit breaker and retry logic."""
        if not self._circuit.can_execute():
            raise CircuitOpenError("Redis circuit breaker is OPEN — failing fast")

        last_error = None
        for attempt in range(max_retries):
            try:
                result = func(self.get_client())
                self._circuit.record_success()
                return result
            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_error = e
                self._circuit.record_failure()
                if attempt < max_retries - 1:
                    backoff = 0.1 * (2 ** attempt)
                    self.log.warning(
                        "redis_retry",
                        attempt=attempt + 1,
                        backoff=backoff,
                        error=str(e),
                    )
                    time.sleep(backoff)

        raise last_error  # type: ignore[misc]

    def ping(self) -> bool:
        try:
            return self.execute_with_retry(lambda r: r.ping())
        except Exception:
            return False

    def close(self):
        self._pool.disconnect()
        self.log.info("redis_pool_closed")

    @property
    def circuit_state(self) -> str:
        return self._circuit.state
