"""Open live streams: at most a few per person, with a replay on reconnect."""

import threading
from collections import Counter
from collections.abc import Callable

from app.contracts.live_events import (
    LiveEventBusAdapterContract,
    LiveEventStreamFacilitatorContract,
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
    OpenLiveStreamContract,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.live_events import LiveEvent, LiveEventReplay
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_strings import LiveEventId
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds
from app.schemas.typings.platform.constrained_strings import ErrorReasonCode
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.schemas.typings.users.prefixed_id import UserId

# Tabs and devices of one person streaming from one API process at once.
DEFAULT_MAX_STREAMS_PER_USER: int = 5
# A refused stream asks again after this long (the cabinet backs off too).
STREAM_LIMIT_RETRY_SECONDS: int = 30

type StreamSlotRelease = Callable[[], None]


class _OpenStream(OpenLiveStreamContract):
    def __init__(
        self,
        replay: LiveEventReplay,
        subscription: LiveEventSubscriptionContract,
        release: StreamSlotRelease,
    ) -> None:
        self._replay: LiveEventReplay = replay
        self._subscription: LiveEventSubscriptionContract = subscription
        self._release: StreamSlotRelease = release
        self._lock: threading.Lock = threading.Lock()
        self._is_closed: bool = False

    @property
    def replay(self) -> LiveEventReplay:
        return self._replay

    def close(self) -> None:
        with self._lock:
            if self._is_closed:
                return

            self._is_closed = True

        self._subscription.cancel()
        self._release()


class LiveEventStreamFacilitator(LiveEventStreamFacilitatorContract):
    """
    Counts the open streams of each person on this process (a limit per
    process: with several API instances a person may reach each of them),
    subscribes a new stream to its business and works out what a
    reconnecting cabinet missed: the events after its `Last-Event-ID`, or a
    resync when this process does not know that id.
    """

    def __init__(
        self,
        bus: LiveEventBusAdapterContract,
        max_streams_per_user: int = DEFAULT_MAX_STREAMS_PER_USER,
    ) -> None:
        self._bus: LiveEventBusAdapterContract = bus
        self._max_streams_per_user: int = max_streams_per_user
        self._lock: threading.Lock = threading.Lock()
        self._streams_per_user: Counter[UserId] = Counter()

    def open(
        self,
        user_id: UserId,
        business_id: BusinessId,
        last_event_id: LiveEventId | None,
        subscriber: LiveEventSubscriberContract,
    ) -> OpenLiveStreamContract:
        self._take_slot(user_id)
        try:
            # Subscribe first: an event published while the replay is read
            # then arrives live (perhaps twice, which only reloads twice).
            subscription: LiveEventSubscriptionContract = self._bus.subscribe(
                business_id, subscriber
            )
            replay: LiveEventReplay = self._replay(business_id, last_event_id)
        except BaseException:
            self._release_slot(user_id)
            raise

        return _OpenStream(replay, subscription, lambda: self._release_slot(user_id))

    def open_stream_count(self, user_id: UserId) -> int:
        with self._lock:
            return self._streams_per_user[user_id]

    def _replay(
        self,
        business_id: BusinessId,
        last_event_id: LiveEventId | None,
    ) -> LiveEventReplay:
        if last_event_id is None:
            return LiveEventReplay()

        missed: list[LiveEvent] | None = self._bus.replay_after(
            business_id, last_event_id
        )
        if missed is None:
            return LiveEventReplay(is_resync_required=True)

        return LiveEventReplay(events=missed)

    def _take_slot(self, user_id: UserId) -> None:
        with self._lock:
            if self._streams_per_user[user_id] >= self._max_streams_per_user:
                raise RateLimitedError(
                    "Too many live streams are open for this person; close "
                    "other tabs of the cabinet.",
                    reasons=[
                        ErrorReason(
                            code=ErrorReasonCode("too_many_live_streams"),
                            message=ErrorReasonMessage(
                                f"At most {self._max_streams_per_user} live "
                                "streams per person."
                            ),
                        )
                    ],
                    retry_after_seconds=RetryAfterSeconds(STREAM_LIMIT_RETRY_SECONDS),
                )

            self._streams_per_user[user_id] += 1

    def _release_slot(self, user_id: UserId) -> None:
        with self._lock:
            self._streams_per_user[user_id] -= 1
            if self._streams_per_user[user_id] <= 0:
                del self._streams_per_user[user_id]
