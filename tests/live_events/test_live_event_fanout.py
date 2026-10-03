"""One process's fan-out: who hears an event, what a reconnect replays, shutdown."""

import logging

import pytest

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.adapters.events.live_event_fanout import LiveEventFanout
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.live_events.live_event_builders import (
    BrokenSubscriber,
    RecordingSubscriber,
    event_id_at,
    make_event,
)


def test_an_event_reaches_only_the_streams_of_its_business() -> None:
    bus = InMemoryLiveEventBusAdapter()
    business_a, business_b = BusinessId(), BusinessId()
    first_a, second_a, stream_b = (
        RecordingSubscriber(),
        RecordingSubscriber(),
        RecordingSubscriber(),
    )
    bus.subscribe(business_a, first_a)
    bus.subscribe(business_a, second_a)
    bus.subscribe(business_b, stream_b)

    event = make_event(business_a, LiveEventKind.HANDOFF_CREATED)
    bus.publish(event)

    assert first_a.events == [event]
    assert second_a.events == [event]
    assert stream_b.events == []


def test_a_cancelled_stream_hears_nothing_more_and_cancelling_twice_is_harmless() -> (
    None
):
    bus = InMemoryLiveEventBusAdapter()
    business_id = BusinessId()
    stream = RecordingSubscriber()
    subscription = bus.subscribe(business_id, stream)

    subscription.cancel()
    subscription.cancel()
    bus.publish(make_event(business_id))

    assert stream.events == []


def test_a_reconnect_replays_the_business_events_after_the_last_seen_one() -> None:
    bus = InMemoryLiveEventBusAdapter()
    business_a, business_b = BusinessId(), BusinessId()
    seen = make_event(business_a)
    missed_a = make_event(business_a, LiveEventKind.LEAD_CREATED)
    other_business = make_event(business_b)
    missed_again = make_event(business_a, LiveEventKind.BOOKING_CHANGED)
    for event in (seen, missed_a, other_business, missed_again):
        bus.publish(event)

    assert bus.replay_after(business_a, seen.id) == [missed_a, missed_again]
    assert bus.replay_after(business_a, missed_again.id) == []


def test_an_unknown_last_event_means_a_resync() -> None:
    bus = InMemoryLiveEventBusAdapter()
    business_id = BusinessId()
    bus.publish(make_event(business_id))

    assert bus.replay_after(business_id, event_id_at(1)) is None


def test_old_events_leave_the_replay_history() -> None:
    fanout = LiveEventFanout(replay_capacity=2)
    business_id = BusinessId()
    oldest, newer, newest = (make_event(business_id) for _ in range(3))
    for event in (oldest, newer, newest):
        fanout.dispatch(event)

    assert fanout.replay_after(business_id, oldest.id) is None
    assert fanout.replay_after(business_id, newer.id) == [newest]


def test_a_resync_forgets_the_history_and_tells_every_stream() -> None:
    fanout = LiveEventFanout()
    business_a, business_b = BusinessId(), BusinessId()
    stream_a, stream_b = RecordingSubscriber(), RecordingSubscriber()
    fanout.subscribe(business_a, stream_a)
    fanout.subscribe(business_b, stream_b)
    seen = make_event(business_a)
    fanout.dispatch(seen)

    fanout.resync_all()

    assert (stream_a.resyncs, stream_b.resyncs) == (1, 1)
    assert fanout.replay_after(business_a, seen.id) is None


def test_closing_ends_every_stream_and_refuses_new_ones() -> None:
    bus = InMemoryLiveEventBusAdapter()
    business_id = BusinessId()
    open_stream = RecordingSubscriber()
    bus.subscribe(business_id, open_stream)

    bus.close()
    late_stream = RecordingSubscriber()
    bus.subscribe(business_id, late_stream)
    bus.publish(make_event(business_id))

    assert open_stream.ended == 1
    assert late_stream.ended == 1
    assert open_stream.events == [] and late_stream.events == []


def test_a_broken_stream_does_not_keep_the_event_from_the_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fanout = LiveEventFanout()
    business_id = BusinessId()
    healthy = RecordingSubscriber()
    fanout.subscribe(business_id, BrokenSubscriber())
    fanout.subscribe(business_id, healthy)
    event = make_event(business_id)

    with caplog.at_level(logging.ERROR):
        fanout.dispatch(event)
        fanout.resync_all()
        fanout.close()

    assert healthy.events == [event]
    assert (healthy.resyncs, healthy.ended) == (1, 1)
    assert "failed to take an event" in caplog.text
