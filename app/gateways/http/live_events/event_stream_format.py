"""
The wire format of the live stream (Server-Sent Events, text/event-stream):

    retry: 3000                      once, the browser's reconnect pause

    event: stream.ready              first, with the stream's timings
    data: {"heartbeat_seconds": 20.0, "lifetime_seconds": 900.0}

    id: 01790812800000000-9f8e7d6c   a change in the business
    event: booking.created
    data: {"event": "booking.created", "ids": ["booking_…"], "occurred_at": …}

    event: stream.resync             reload everything shown
    data: {}

    : heartbeat                      a comment while nothing happens
"""

import json

from app.schemas.constants.live_events import LiveStreamSignal
from app.schemas.dto.live_events import LiveEvent, LiveStreamLimits

RETRY_MILLISECONDS: int = 3000
HEARTBEAT: bytes = b": heartbeat\n\n"
EVENT_STREAM_MEDIA_TYPE: str = "text/event-stream"


def format_opening(limits: LiveStreamLimits) -> bytes:
    """The reconnect pause and `stream.ready` with the stream's timings."""

    timings: dict[str, float] = {
        "heartbeat_seconds": float(limits.heartbeat_seconds),
        "lifetime_seconds": float(limits.lifetime_seconds),
    }
    return f"retry: {RETRY_MILLISECONDS}\n\n".encode() + _message(
        LiveStreamSignal.READY.value, json.dumps(timings)
    )


def format_resync() -> bytes:
    return _message(LiveStreamSignal.RESYNC.value, "{}")


def format_event(event: LiveEvent) -> bytes:
    """One change: its id (for Last-Event-ID), kind, ids and time."""

    data: str = json.dumps(
        {
            "event": event.event.value,
            "ids": [str(subject_id) for subject_id in event.ids],
            "occurred_at": int(event.occurred_at),
        },
        separators=(",", ":"),
    )
    return f"id: {event.id}\n".encode() + _message(event.event.value, data)


def _message(name: str, data: str) -> bytes:
    return f"event: {name}\ndata: {data}\n\n".encode()
