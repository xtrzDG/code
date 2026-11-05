"""
The streams of one process and the events it heard lately: both live event
buses hand every event to `dispatch`, which passes it to the subscribers of
its business and keeps it for reconnecting cabinets (`replay_after`).
"""

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from app.contracts.live_events import (
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.schemas.constants.live_events import WIDGET_LIVE_EVENTS
from app.schemas.dto.live_events import LiveEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import LiveEventId

LOGGER: logging.Logger = logging.getLogger(__name__)

# Events of all businesses kept for replay: a cabinet that reconnects within
# a few minutes (a phone waking up, a deploy) gets what it missed; one that
# comes back later reloads everything.
DEFAULT_REPLAY_CAPACITY: int = 2000

type SubscriberAction = Callable[[LiveEventSubscriberContract], None]


@dataclass(eq=False)
class _Subscription(LiveEventSubscriptionContract):
    fanout: LiveEventFanout
    business_id: BusinessId
    subscriber: LiveEventSubscriberContract

    def cancel(self) -> None:
        self.fanout.remove(self)


class LiveEventFanout:
    """Thread-safe fan-out of live events to the streams of this process."""

    def __init__(self, replay_capacity: int = DEFAULT_REPLAY_CAPACITY) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._subscriptions: dict[BusinessId, list[_Subscription]] = {}
        self._recent: deque[LiveEvent] = deque(maxlen=replay_capacity)
        self._is_closed: bool = False

    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        subscription = _Subscription(self, business_id, subscriber)
        with self._lock:
            is_closed: bool = self._is_closed
            if not is_closed:
                self._subscriptions.setdefault(business_id, []).append(subscription)

        if is_closed:
            subscriber.end()

        return subscription

    def remove(self, subscription: _Subscription) -> None:
        with self._lock:
            business_subscriptions = self._subscriptions.get(subscription.business_id)
            if (
                business_subscriptions is None
                or subscription not in business_subscriptions
            ):
                return

            business_subscriptions.remove(subscription)
            if not business_subscriptions:
                del self._subscriptions[subscription.business_id]

    def dispatch(self, event: LiveEvent) -> None:
        """Keep the event for replay and hand it to its business's streams."""

        with self._lock:
            # The widget's events are not replayed (a widget polls once
            # when it reconnects); they would crowd the cabinets' history.
            if event.event not in WIDGET_LIVE_EVENTS:
                self._recent.append(event)
            receivers: list[_Subscription] = list(
                self._subscriptions.get(event.business_id, ())
            )

        for subscription in receivers:
            self._call(subscription, lambda target: target.deliver(event))

    def resync_all(self) -> None:
        """
        Events may have been lost (the listener reconnected): forget the
        replay history, which now has a gap, and ask every stream to reload.
        """

        with self._lock:
            self._recent.clear()
            receivers: list[_Subscription] = self._all_subscriptions()

        for subscription in receivers:
            self._call(subscription, lambda target: target.resync())

    def replay_after(
        self,
        business_id: BusinessId,
        event_id: LiveEventId,
    ) -> list[LiveEvent] | None:
        with self._lock:
            recent: list[LiveEvent] = list(self._recent)

        for index, event in enumerate(recent):
            if event.id == event_id:
                return [
                    later
                    for later in recent[index + 1 :]
                    if later.business_id == business_id
                ]

        return None

    def close(self) -> None:
        """End every stream and refuse new ones (shutdown)."""

        with self._lock:
            self._is_closed = True
            receivers: list[_Subscription] = self._all_subscriptions()
            self._subscriptions.clear()

        for subscription in receivers:
            self._call(subscription, lambda target: target.end())

    def _all_subscriptions(self) -> list[_Subscription]:
        return [
            subscription
            for business_subscriptions in self._subscriptions.values()
            for subscription in business_subscriptions
        ]

    @staticmethod
    def _call(subscription: _Subscription, action: SubscriberAction) -> None:
        # One broken stream must not keep the event from the others.
        try:
            action(subscription.subscriber)
        except Exception:  # noqa: BLE001 - isolate subscribers from each other
            LOGGER.exception("A live event stream failed to take an event")
