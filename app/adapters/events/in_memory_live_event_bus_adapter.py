"""Live events inside one process: development without Postgres, and tests."""

from app.adapters.events.live_event_fanout import LiveEventFanout
from app.contracts.live_events import (
    LiveEventBusAdapterContract,
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import LiveEventId


class InMemoryLiveEventBusAdapter(LiveEventBusAdapterContract):
    """
    Hands every event straight to the streams of this process. Without
    DATABASE_URL the background worker runs inside the API process
    (EMBEDDED_WORKER), so the events of incoming messages reach the
    cabinet too.
    """

    def __init__(self, fanout: LiveEventFanout | None = None) -> None:
        self._fanout: LiveEventFanout = fanout or LiveEventFanout()

    def publish(self, event: LiveEvent) -> None:
        self._fanout.dispatch(event)

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        return self._fanout.subscribe(business_id, subscriber)

    def replay_after(
        self,
        business_id: BusinessId,
        event_id: LiveEventId,
    ) -> list[LiveEvent] | None:
        return self._fanout.replay_after(business_id, event_id)

    def close(self) -> None:
        self._fanout.close()
