"""
Website chat visitors' live streams: each hears only its own visitor's
widget events, and a business or a client network holds a bounded number
of them on one API process.
"""

import threading
from collections import Counter
from collections.abc import Callable

from app.contracts.live_events import (
    LiveEventBusAdapterContract,
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.contracts.widget_streams import WidgetEventStreamFacilitatorContract
from app.schemas.constants.live_events import WIDGET_LIVE_EVENTS
from app.schemas.dto.channels.widget_streams import WidgetStreamLimits
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.live_events import LiveEvent
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage

# A refused stream: the widget polls instead and tries the stream again later.
STREAM_LIMIT_RETRY_SECONDS: int = 60

type SlotKey = tuple[str, str]


class VisitorEventFilter(LiveEventSubscriberContract):
    """
    Passes on the business's widget events that name `visitor_id` first;
    everything else of the business (the cabinet's events, other
    visitors') stays out. Resyncs and the end go through.
    """

    def __init__(
        self,
        visitor_id: WidgetVisitorId,
        subscriber: LiveEventSubscriberContract,
    ) -> None:
        self._visitor: str = str(visitor_id)
        self._subscriber: LiveEventSubscriberContract = subscriber

    def deliver(self, event: LiveEvent) -> None:
        if event.event in WIDGET_LIVE_EVENTS and event.ids[:1] == [self._visitor]:
            self._subscriber.deliver(event)

    def resync(self) -> None:
        self._subscriber.resync()

    def end(self) -> None:
        self._subscriber.end()


class _OpenWidgetStream(LiveEventSubscriptionContract):
    def __init__(
        self,
        subscription: LiveEventSubscriptionContract,
        release: Callable[[], None],
    ) -> None:
        self._subscription: LiveEventSubscriptionContract = subscription
        self._release: Callable[[], None] = release
        self._lock: threading.Lock = threading.Lock()
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        with self._lock:
            if self._is_cancelled:
                return

            self._is_cancelled = True

        self._subscription.cancel()
        self._release()


class WidgetEventStreamFacilitator(WidgetEventStreamFacilitatorContract):
    """
    Counts the open visitor streams per business and per client network on
    this process (thread-safe) and subscribes each, filtered to its
    visitor, to its business on the live event bus. No replay: a widget
    that (re)connects polls its messages once instead.
    """

    def __init__(
        self,
        bus: LiveEventBusAdapterContract,
        limits: WidgetStreamLimits,
    ) -> None:
        self._bus: LiveEventBusAdapterContract = bus
        self._limits: WidgetStreamLimits = limits
        self._lock: threading.Lock = threading.Lock()
        self._open: Counter[SlotKey] = Counter()

    def open(
        self,
        business_id: BusinessId,
        visitor_id: WidgetVisitorId,
        client_ip_address: ClientIpAddress | None,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        keys: list[SlotKey] = self._take_slots(business_id, client_ip_address)
        try:
            subscription: LiveEventSubscriptionContract = self._bus.subscribe(
                business_id, VisitorEventFilter(visitor_id, subscriber)
            )
        except BaseException:
            self._release(keys)
            raise

        return _OpenWidgetStream(subscription, lambda: self._release(keys))

    def open_stream_count(self, business_id: BusinessId) -> int:
        with self._lock:
            return self._open[("business", str(business_id))]

    def _take_slots(
        self,
        business_id: BusinessId,
        client_ip_address: ClientIpAddress | None,
    ) -> list[SlotKey]:
        business_key: SlotKey = ("business", str(business_id))
        keys: list[SlotKey] = [business_key]
        if client_ip_address is not None:
            keys.append(("address", str(client_ip_address)))

        with self._lock:
            if self._open[business_key] >= int(self._limits.streams_per_business):
                raise too_many_streams("too_many_widget_streams")

            if len(keys) > 1 and self._open[keys[1]] >= int(
                self._limits.streams_per_address
            ):
                raise too_many_streams("too_many_widget_streams_from_address")

            for key in keys:
                self._open[key] += 1

        return keys

    def _release(self, keys: list[SlotKey]) -> None:
        with self._lock:
            for key in keys:
                self._open[key] -= 1
                if self._open[key] <= 0:
                    del self._open[key]


def too_many_streams(code: str) -> RateLimitedError:
    return RateLimitedError(
        "Too many live chat streams are open; the chat checks for answers instead.",
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(code),
                message=ErrorReasonMessage(
                    "The website chat falls back to polling for a while."
                ),
            )
        ],
        retry_after_seconds=RetryAfterSeconds(STREAM_LIMIT_RETRY_SECONDS),
    )
