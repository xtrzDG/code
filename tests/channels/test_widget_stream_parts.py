"""
The parts of the widget's live stream: tickets, visitor ids, the per
process limits and the stream's chunks.
"""

import asyncio
from uuid import UUID

import pytest
from typed_time_provider import Microseconds

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.facilitators.events.widget_event_stream_facilitator import (
    WidgetEventStreamFacilitator,
)
from app.gateways.http.live_events.event_stream_subscriber import (
    EventStreamSubscriber,
)
from app.gateways.http.live_events.widget_event_chunks import widget_event_chunks
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.channels.widget_streams import (
    WidgetStreamClaims,
    WidgetStreamLimits,
    WidgetStreamMessageView,
)
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import (
    WidgetStreamsPerAddress,
    WidgetStreamsPerBusiness,
)
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.security.widget_stream_ticket_signer import (
    WidgetStreamTicketSigner,
)
from tests.channels.widget_stream_api import widget_event
from tests.live_events.live_api import parse_stream
from tests.live_events.live_event_builders import RecordingSubscriber

KEY: str = "v1_9f2c4e1b7a3d48c6"
CLAIMS: WidgetStreamClaims = WidgetStreamClaims(
    business_id=BusinessId(UUID("0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01")),
    visitor_id=widget_visitor_id(KEY),
    expires_at=Microseconds(1_790_816_400_000_000),
)


def test_a_ticket_reads_back_and_rejects_forgery_and_other_keys() -> None:
    signer = WidgetStreamTicketSigner(PlatformSecret("test-key-0000"))
    ticket = signer.sign(CLAIMS)

    assert signer.read(ticket) == CLAIMS
    assert KEY not in str(ticket)
    tampered = (
        str(ticket)[:10] + ("B" if str(ticket)[10] != "B" else "C") + str(ticket)[11:]
    )
    assert signer.read(WidgetStreamTicket(tampered)) is None
    assert signer.read(WidgetStreamTicket("A" * 66)) is None
    assert signer.read(WidgetStreamTicket("A" * 67)) is None
    assert signer.read(WidgetStreamTicket(str(ticket) + "A")) is None
    other = WidgetStreamTicketSigner(PlatformSecret("test-key-1111"))
    assert other.read(ticket) is None
    rotated = WidgetStreamTicketSigner(
        PlatformSecret("test-key-1111"), previous_keys=[PlatformSecret("test-key-0000")]
    )
    assert rotated.read(ticket) == CLAIMS


def test_a_process_without_an_encryption_key_still_signs_its_own_tickets() -> None:
    signer = WidgetStreamTicketSigner(None)

    assert signer.read(signer.sign(CLAIMS)) == CLAIMS
    assert WidgetStreamTicketSigner(None).read(signer.sign(CLAIMS)) is None


def test_a_visitor_id_is_stable_one_way_and_distinct() -> None:
    assert widget_visitor_id(KEY) == widget_visitor_id(KEY)
    assert widget_visitor_id(KEY) != widget_visitor_id("v1_someone_else_entirely_42")
    assert KEY.removeprefix("v1_") not in str(widget_visitor_id(KEY))


def test_streams_are_limited_per_business_and_per_network() -> None:
    limits = WidgetStreamLimits(
        streams_per_business=WidgetStreamsPerBusiness(3),
        streams_per_address=WidgetStreamsPerAddress(2),
    )
    streams = WidgetEventStreamFacilitator(InMemoryLiveEventBusAdapter(), limits)
    business = BusinessId()
    office = ClientIpAddress("203.0.113.7")
    visitor = widget_visitor_id(KEY)

    first = streams.open(business, visitor, office, RecordingSubscriber())
    streams.open(business, visitor, office, RecordingSubscriber())
    with pytest.raises(RateLimitedError) as from_network:
        streams.open(business, visitor, office, RecordingSubscriber())
    streams.open(
        business, visitor, ClientIpAddress("198.51.100.1"), RecordingSubscriber()
    )
    with pytest.raises(RateLimitedError) as from_business:
        streams.open(business, visitor, None, RecordingSubscriber())

    assert from_network.value.retry_after_seconds == 60
    assert from_business.value.reasons[0].code == "too_many_widget_streams"
    first.cancel()
    first.cancel()
    assert streams.open_stream_count(business) == 2
    streams.open(business, visitor, office, RecordingSubscriber())


def test_the_heartbeat_keeps_a_quiet_stream_and_the_lifetime_ends_it() -> None:
    times = iter([0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0])
    limits = WidgetStreamLimits(
        heartbeat_seconds=LiveStreamHeartbeatSeconds(0.5),
        lifetime_seconds=LiveStreamLifetimeSeconds(1.0),
    )

    async def never(message_id: MessageId) -> WidgetStreamMessageView | None:
        raise AssertionError(message_id)

    async def scenario() -> str:
        subscriber = EventStreamSubscriber(asyncio.get_running_loop())
        subscriber.resync()
        chunks = widget_event_chunks(
            subscriber, limits, never, clock=lambda: next(times)
        )
        return b"".join([chunk async for chunk in chunks]).decode()

    text = asyncio.run(scenario())

    assert [message.event for message in parse_stream(text)] == [
        "stream.ready",
        "stream.resync",
    ]
    assert text.count(": heartbeat\n\n") == 1


def test_an_answer_keeps_its_lines_in_one_data_field() -> None:
    business = BusinessId()
    message_id = MessageId()

    async def read(asked: MessageId) -> WidgetStreamMessageView | None:
        return WidgetStreamMessageView(
            message_id=asked,
            author=MessageAuthor.ASSISTANT,
            text=MessageText("Line one\nLine two"),
        )

    async def scenario() -> str:
        subscriber = EventStreamSubscriber(asyncio.get_running_loop())
        subscriber.deliver(
            widget_event(business, LiveEventKind.WIDGET_REPLY, KEY, str(message_id))
        )
        subscriber.end()
        chunks = widget_event_chunks(subscriber, WidgetStreamLimits(), read)
        return b"".join([chunk async for chunk in chunks]).decode()

    text = asyncio.run(scenario())

    [ready, answer] = parse_stream(text)
    assert answer.data["text"] == "Line one\nLine two"
    assert "data: {" in text and "Line one\\nLine two" in text
    assert ready.event == "stream.ready"
