"""What one live stream sends, from its opening to its end."""

import time
from collections.abc import AsyncIterator, Callable

from app.gateways.http.live_events.event_stream_format import (
    HEARTBEAT,
    format_event,
    format_opening,
    format_resync,
)
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
    StreamControl,
)
from app.schemas.constants.live_events import WIDGET_LIVE_EVENTS
from app.schemas.dto.live_events import LiveEventReplay, LiveStreamLimits

type MonotonicSeconds = Callable[[], float]


async def live_event_chunks(
    replay: LiveEventReplay,
    subscriber: EventStreamSubscriber,
    limits: LiveStreamLimits,
    clock: MonotonicSeconds = time.monotonic,
) -> AsyncIterator[bytes]:
    """
    `stream.ready`, then what a reconnecting cabinet missed (the events, or
    `stream.resync`), then every event of the business as it comes, with a
    heartbeat after each quiet `heartbeat_seconds`, until the bus ends the
    stream or its lifetime is over (the cabinet reconnects). The website
    chat visitors' own events (`WIDGET_LIVE_EVENTS`) are not the cabinet's.
    """

    yield format_opening(limits)
    if replay.is_resync_required:
        yield format_resync()

    for event in replay.events:
        if event.event not in WIDGET_LIVE_EVENTS:
            yield format_event(event)

    heartbeat_seconds: float = float(limits.heartbeat_seconds)
    deadline: float = clock() + float(limits.lifetime_seconds)
    while (remaining := deadline - clock()) > 0:
        item = await subscriber.next_item(min(heartbeat_seconds, remaining))
        if item is None:
            if deadline - clock() > 0:
                yield HEARTBEAT
            continue

        if item is StreamControl.END:
            return

        if item is StreamControl.RESYNC:
            yield format_resync()
        elif item.event not in WIDGET_LIVE_EVENTS:
            yield format_event(item)
