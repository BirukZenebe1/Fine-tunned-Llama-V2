"""User activity event producer — simulates page views, clicks, and purchases."""

import random
import string
import time
import uuid

from config import Settings
from producers.base_producer import BaseProducer
from producers.schemas import ActivityEvent, EventType

PAGES = [
    "/",
    "/products",
    "/products/electronics",
    "/products/clothing",
    "/products/books",
    "/cart",
    "/checkout",
    "/about",
    "/support",
    "/account",
]

EVENT_WEIGHTS = {
    EventType.PAGE_VIEW: 0.60,
    EventType.CLICK: 0.30,
    EventType.PURCHASE: 0.10,
}


class ActivityProducer(BaseProducer):
    def __init__(self, settings: Settings):
        super().__init__(settings, "activity-producer")
        self._interval = 1.0 / settings.activity_events_per_sec
        self._active_sessions: dict[str, str] = {}  # session_id -> user_id
        self.log.info(
            "activity_producer_configured",
            events_per_sec=settings.activity_events_per_sec,
        )

    def _get_session(self) -> tuple[str, str]:
        """Get or create a user session with realistic churn."""
        # 10% chance of new session
        if not self._active_sessions or random.random() < 0.10:
            session_id = str(uuid.uuid4())[:8]
            user_id = f"user-{''.join(random.choices(string.ascii_lowercase, k=4))}"
            self._active_sessions[session_id] = user_id
            # Cap active sessions to prevent unbounded growth
            if len(self._active_sessions) > 100:
                oldest = next(iter(self._active_sessions))
                del self._active_sessions[oldest]
        else:
            session_id = random.choice(list(self._active_sessions.keys()))
            user_id = self._active_sessions[session_id]

        # 5% chance of ending session
        if random.random() < 0.05 and len(self._active_sessions) > 1:
            self._active_sessions.pop(session_id, None)

        return session_id, user_id

    def _pick_event_type(self) -> EventType:
        r = random.random()
        cumulative = 0.0
        for event_type, weight in EVENT_WEIGHTS.items():
            cumulative += weight
            if r <= cumulative:
                return event_type
        return EventType.PAGE_VIEW

    def generate_event(self) -> tuple[str, str, dict]:
        session_id, user_id = self._get_session()
        event_type = self._pick_event_type()
        page = random.choice(PAGES)

        value = None
        if event_type == EventType.PURCHASE:
            value = round(random.uniform(9.99, 299.99), 2)

        event = ActivityEvent(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            page=page,
            value=value,
            timestamp=time.time() * 1000,
        )
        return (self.settings.topic_activity_raw, event.partition_key(), event.model_dump())

    def get_interval(self) -> float:
        # Poisson-like intervals
        return random.expovariate(1.0 / self._interval)


if __name__ == "__main__":
    settings = Settings()
    producer = ActivityProducer(settings)
    producer.run()
