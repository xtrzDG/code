"""
What a website visitor's live stream sends (Server-Sent Events):

    retry: 3000                      once, the browser's reconnect pause

    event: stream.ready              first, with the stream's timings
    data: {"heartbeat_seconds": 20.0, "lifetime_seconds": 900.0}

    event: typing_started            a worker is writing the visitor's answer
    data: {}

    event: answer_ready              something for the visitor is stored
    data: {"message_id": "message_…", "author": "assistant",
           "text": "…", "direction": "ltr"}

    event: stream.resync             events may be lost: poll once
    data: {}

    : heartbeat                      a comment while nothing happens

`answer_ready` carries the text only when the reply guard passed the
model's reply as CLEAN (see `ReadWidgetStreamMessageUseCase`); without
`text` (or without a message, `{}`) the widget polls for it. No event has
an `id`: a reconnecting widget polls once instead of replaying.
"""

import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from app.gateways.http.live_events.event_stream_chunks import MonotonicSeconds
from app.gateways.http.live_events.event_stream_format import (
    HEARTBEAT,
    format_opening,
    format_resync,
)
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
    StreamControl,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamLimits,
    WidgetStreamMessageView,
)
from app.schemas.dto.live_events import LiveEvent, LiveStreamLimits
from app.schemas.typings.conversations.prefixed_id import MessageId

TYPING_STARTED: str = "typing_started"
ANSWER_READY: str = "answer_ready"

type ReadStreamMessage = Callable[
    [MessageId], Awaitable[WidgetStreamMessageView | None]
]


async def widget_event_chunks(
    subscriber: EventStreamSubscriber,
    limits: WidgetStreamLimits,
    read_message: ReadStreamMessage,
    clock: MonotonicSeconds = time.monotonic,
) -> AsyncIterator[bytes]:
    """
    `stream.ready`, then the visitor's events as they come, in the order
    they were published, with a heartbeat after each quiet
    `heartbeat_seconds`, until the bus ends the stream or its lifetime is
    over (the widget reconnects with the same ticket).
    """

    yield format_opening(
        LiveStreamLimits(
            heartbeat_seconds=limits.heartbeat_seconds,
            lifetime_seconds=limits.lifetime_seconds,
        )
    )
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
            continue

        yield await format_widget_event(item, read_message)


async def format_widget_event(
    event: LiveEvent,
    read_message: ReadStreamMessage,
) -> bytes:
    if event.event is LiveEventKind.WIDGET_TYPING:
        return widget_message(TYPING_STARTED, {})

    view: WidgetStreamMessageView | None = None
    if len(event.ids) > 1:
        view = await read_message(MessageId(str(event.ids[1])))

    return widget_message(ANSWER_READY, {} if view is None else answer_data(view))


def answer_data(view: WidgetStreamMessageView) -> dict[str, str]:
    data: dict[str, str] = {
        "message_id": str(view.message_id),
        "author": view.author.value,
        "direction": view.direction.value,
    }
    if view.text is not None:
        data["text"] = str(view.text)

    return data


def widget_message(name: str, data: dict[str, str]) -> bytes:
    payload: str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {payload}\n\n".encode()
