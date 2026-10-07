"""A live event bus that tells a test when a stream has subscribed."""

import threading
from collections.abc import Sequence

from app.contracts.live_events import (
    LiveEventBusAdapterContract,
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import LiveEventId


class SubscriptionSignallingBus(LiveEventBusAdapterContract):
    """
    Passes everything to the real bus and sets `subscribed` once a stream
    has subscribed, so a test acts on an open stream rather than guessing
    how long opening one takes on a busy machine. Events handed to
    `publish_on_subscribe` go on the bus the moment the next stream has
    subscribed, before its lifetime starts, so a slow test thread can
    never miss a short-lived stream.
    """

    def __init__(self, bus: LiveEventBusAdapterContract) -> None:
        self._bus: LiveEventBusAdapterContract = bus
        self.subscribed: threading.Event = threading.Event()
        self._on_subscribe: list[LiveEvent] = []

    def publish_on_subscribe(self, events: Sequence[LiveEvent]) -> None:
        self._on_subscribe = list(events)

    def publish(self, event: LiveEvent) -> None:
        self._bus.publish(event)

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        subscription: LiveEventSubscriptionContract = self._bus.subscribe(
            business_id, subscriber
        )
        pending, self._on_subscribe = self._on_subscribe, []
        for event in pending:
            self._bus.publish(event)
        self.subscribed.set()
        return subscription

    def replay_after(
        self,
        business_id: BusinessId,
        event_id: LiveEventId,
    ) -> list[LiveEvent] | None:
        return self._bus.replay_after(business_id, event_id)

    def close(self) -> None:
        self._bus.close()
