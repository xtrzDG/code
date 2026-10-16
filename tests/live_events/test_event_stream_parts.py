"""The parts of an SSE response: the thread bridge, the chunks, the response."""

import asyncio
from collections.abc import AsyncIterator

from starlette.types import Message

from app.gateways.http.live_events.event_stream_chunks import live_event_chunks
from app.gateways.http.live_events.event_stream_response import EventStreamResponse
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
    StreamControl,
)
from app.schemas.dto.live_events import LiveEventReplay, LiveStreamLimits
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)
from tests.live_events.live_event_builders import make_event


def test_a_slow_client_gets_one_resync_instead_of_a_backlog() -> None:
    async def scenario() -> list[object]:
        subscriber = EventStreamSubscriber(asyncio.get_running_loop(), capacity=2)
        business_id = BusinessId()
        for _ in range(5):
            subscriber.deliver(make_event(business_id))
        subscriber.end()
        await asyncio.sleep(0)
        return [await subscriber.next_item(0.1) for _ in range(3)]

    first, second, third = asyncio.run(scenario())

    assert first is StreamControl.RESYNC
    assert second is StreamControl.END
    assert third is None


def test_events_for_a_stream_whose_loop_is_gone_are_dropped() -> None:
    loop = asyncio.new_event_loop()
    subscriber = EventStreamSubscriber(loop)
    loop.close()

    subscriber.deliver(make_event(BusinessId()))
    subscriber.resync()


def test_the_heartbeat_waits_for_the_quiet_and_the_lifetime_ends_the_stream() -> None:
    times = iter([0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0])
    limits = LiveStreamLimits(
        heartbeat_seconds=LiveStreamHeartbeatSeconds(0.5),
        lifetime_seconds=LiveStreamLifetimeSeconds(1.0),
    )

    async def scenario() -> list[bytes]:
        subscriber = EventStreamSubscriber(asyncio.get_running_loop())
        subscriber.resync()
        chunks = live_event_chunks(
            LiveEventReplay(), subscriber, limits, clock=lambda: next(times)
        )
        return [chunk async for chunk in chunks]

    chunks = asyncio.run(scenario())

    assert chunks[0].startswith(b"retry: 3000\n\nevent: stream.ready")
    assert b"event: stream.resync" in chunks[1]
    assert chunks[2:] == [b": heartbeat\n\n"]


class Closable:
    """An endless chunk source that notes being closed."""

    def __init__(self) -> None:
        self.is_closed: bool = False

    async def chunks(self) -> AsyncIterator[bytes]:
        try:
            while True:
                yield b": heartbeat\n\n"
                await asyncio.sleep(0.01)
        finally:
            self.is_closed = True


def run_response(send_fails: bool) -> tuple[int, bool, list[Message]]:
    source = Closable()
    closed: list[int] = []
    sent: list[Message] = []
    chunks = source.chunks()

    async def receive() -> Message:
        await asyncio.sleep(0.05)
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        if send_fails and message["type"] == "http.response.body":
            raise OSError("the client went away")
        sent.append(message)

    async def scenario() -> None:
        response = EventStreamResponse(chunks, on_close=lambda: closed.append(1))
        await response({"type": "http"}, receive, send)

    asyncio.run(scenario())
    return len(closed), source.is_closed, sent


def test_a_client_that_goes_away_ends_the_stream_and_closes_it_once() -> None:
    closed, is_source_closed, sent = run_response(send_fails=False)

    assert closed == 1
    assert is_source_closed
    assert sent[0]["type"] == "http.response.start"


def test_a_write_to_a_gone_client_ends_the_stream_quietly() -> None:
    closed, _, sent = run_response(send_fails=True)

    assert closed == 1
    assert [message["type"] for message in sent] == ["http.response.start"]
