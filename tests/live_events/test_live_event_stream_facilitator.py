"""Opening streams: the replay a reconnect gets and the limit per person."""

import pytest

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.contracts.live_events import (
    LiveEventSubscriberContract,
    LiveEventSubscriptionContract,
)
from app.facilitators.events.live_event_stream_facilitator import (
    LiveEventStreamFacilitator,
)
from app.schemas.dto.live_events import LiveStreamLimits
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.live_events.constrained_integers import LiveStreamsPerUser
from app.schemas.typings.users.prefixed_id import UserId
from tests.live_events.live_event_builders import (
    RecordingSubscriber,
    event_id_at,
    make_event,
)

TWO_PER_USER: LiveStreamLimits = LiveStreamLimits(
    streams_per_user=LiveStreamsPerUser(2)
)


class FailingSubscribeBus(InMemoryLiveEventBusAdapter):
    def subscribe(
        self,
        business_id: BusinessId,
        subscriber: LiveEventSubscriberContract,
    ) -> LiveEventSubscriptionContract:
        raise RuntimeError("the listener cannot start")


def test_a_first_connection_replays_nothing_and_hears_new_events() -> None:
    bus = InMemoryLiveEventBusAdapter()
    streams = LiveEventStreamFacilitator(bus, LiveStreamLimits())
    business_id, subscriber = BusinessId(), RecordingSubscriber()

    opened = streams.open(UserId(), business_id, None, subscriber)
    event = make_event(business_id)
    bus.publish(event)

    assert opened.replay.events == [] and not opened.replay.is_resync_required
    assert subscriber.events == [event]


def test_a_reconnect_gets_what_it_missed_or_a_resync() -> None:
    bus = InMemoryLiveEventBusAdapter()
    streams = LiveEventStreamFacilitator(bus, LiveStreamLimits())
    business_id = BusinessId()
    seen, missed = make_event(business_id), make_event(business_id)
    bus.publish(seen)
    bus.publish(missed)

    known = streams.open(UserId(), business_id, seen.id, RecordingSubscriber())
    unknown = streams.open(UserId(), business_id, event_id_at(1), RecordingSubscriber())

    assert known.replay.events == [missed]
    assert not known.replay.is_resync_required
    assert unknown.replay.is_resync_required


def test_a_person_has_a_few_streams_and_closing_one_frees_its_place() -> None:
    streams = LiveEventStreamFacilitator(InMemoryLiveEventBusAdapter(), TWO_PER_USER)
    user_id, other_user, business_id = UserId(), UserId(), BusinessId()
    first = streams.open(user_id, business_id, None, RecordingSubscriber())
    streams.open(user_id, business_id, None, RecordingSubscriber())

    with pytest.raises(RateLimitedError) as refused:
        streams.open(user_id, business_id, None, RecordingSubscriber())

    assert refused.value.retry_after_seconds == 30
    assert [str(reason.code) for reason in refused.value.reasons] == [
        "too_many_live_streams"
    ]
    streams.open(other_user, business_id, None, RecordingSubscriber())
    first.close()
    first.close()
    assert streams.open_stream_count(user_id) == 1
    streams.open(user_id, business_id, None, RecordingSubscriber())
    assert streams.open_stream_count(user_id) == 2


def test_a_closed_stream_hears_nothing_and_its_person_has_no_place_left() -> None:
    bus = InMemoryLiveEventBusAdapter()
    streams = LiveEventStreamFacilitator(bus, LiveStreamLimits())
    user_id, business_id, subscriber = UserId(), BusinessId(), RecordingSubscriber()
    opened = streams.open(user_id, business_id, None, subscriber)

    opened.close()
    bus.publish(make_event(business_id))

    assert subscriber.events == []
    assert streams.open_stream_count(user_id) == 0


def test_a_stream_that_cannot_subscribe_gives_its_place_back() -> None:
    streams = LiveEventStreamFacilitator(FailingSubscribeBus(), TWO_PER_USER)
    user_id = UserId()

    with pytest.raises(RuntimeError):
        streams.open(user_id, BusinessId(), None, RecordingSubscriber())

    assert streams.open_stream_count(user_id) == 0
