"""Publishing what changed: the event's shape, sandbox silence, lost events."""

import logging
import re

import pytest
from typed_time_provider import Microseconds, WallClock

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.adapters.events.live_event_bus_factory import build_live_event_bus_adapter
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.dto.live_events import MAX_LIVE_EVENT_SUBJECTS, LiveEvent
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from tests.live_events.live_event_builders import RecordingSubscriber

NOW_NANOSECONDS: int = 1_790_812_800_123_456_000
EVENT_ID_PATTERN: re.Pattern[str] = re.compile(r"^01790812800123456-[0-9a-f]{8}$")


def fixed_clock() -> WallClock[Microseconds]:
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: NOW_NANOSECONDS,
    )


class RefusingBus(InMemoryLiveEventBusAdapter):
    def publish(self, event: LiveEvent) -> None:
        raise ExternalServiceError("The database is down.")


def test_the_event_names_the_change_by_id_with_a_fresh_id_and_the_time() -> None:
    bus = InMemoryLiveEventBusAdapter()
    stream = RecordingSubscriber()
    business_id = BusinessId()
    bus.subscribe(business_id, stream)
    publisher = EventPublisherFacilitator(bus, fixed_clock())
    handoff_id, conversation_id = HandoffId(), ConversationId()

    publisher.publish(
        business_id, LiveEventKind.HANDOFF_CREATED, (handoff_id, conversation_id)
    )
    publisher.publish(business_id, LiveEventKind.HANDOFF_CREATED)

    first, second = stream.events
    assert first.business_id == business_id
    assert first.event is LiveEventKind.HANDOFF_CREATED
    assert [str(subject) for subject in first.ids] == [
        str(handoff_id),
        str(conversation_id),
    ]
    assert first.occurred_at == NOW_NANOSECONDS // 1000
    assert EVENT_ID_PATTERN.match(str(first.id))
    assert first.id != second.id
    assert second.ids == []


def test_an_event_names_at_most_a_few_things() -> None:
    bus = InMemoryLiveEventBusAdapter()
    stream = RecordingSubscriber()
    business_id = BusinessId()
    bus.subscribe(business_id, stream)

    EventPublisherFacilitator(bus, fixed_clock()).publish(
        business_id,
        LiveEventKind.BOOKING_CHANGED,
        [BookingId() for _ in range(MAX_LIVE_EVENT_SUBJECTS + 3)],
    )

    assert len(stream.events[0].ids) == MAX_LIVE_EVENT_SUBJECTS


def test_sandbox_activity_is_not_announced() -> None:
    bus = InMemoryLiveEventBusAdapter()
    stream = RecordingSubscriber()
    business_id = BusinessId()
    bus.subscribe(business_id, stream)

    EventPublisherFacilitator(bus, fixed_clock()).publish(
        business_id, LiveEventKind.BOOKING_CREATED, (BookingId(),), is_sandbox=True
    )

    assert stream.events == []


def test_a_lost_event_is_logged_and_never_fails_the_change(
    caplog: pytest.LogCaptureFixture,
) -> None:
    publisher = EventPublisherFacilitator(RefusingBus(), fixed_clock())

    with caplog.at_level(logging.WARNING):
        publisher.publish(BusinessId(), LiveEventKind.LEAD_CREATED)

    assert "lead.created" in caplog.text
    assert "ExternalServiceError" in caplog.text


def test_without_a_database_the_bus_stays_in_the_process() -> None:
    bus = build_live_event_bus_adapter(None, None, None)

    assert isinstance(bus, InMemoryLiveEventBusAdapter)
