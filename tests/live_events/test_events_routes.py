"""GET /v1/businesses/{id}/events: who may listen, what a stream carries."""

from app.schemas.constants.live_events import LiveEventKind
from app.schemas.typings.users.prefixed_id import UserId
from tests.live_events.live_api import (
    OTHER_OWNER_TOKEN,
    OWNER_TOKEN,
    STAFF_TOKEN,
    LiveApi,
    parse_stream,
)
from tests.live_events.live_event_builders import RecordingSubscriber, make_event


def test_a_stream_opens_and_carries_the_events_of_its_business_only() -> None:
    api = LiveApi()
    own = make_event(api.business.id, LiveEventKind.HANDOFF_CREATED, "handoff_1234abcd")
    foreign = make_event(api.other_business.id, LiveEventKind.HANDOFF_CREATED)

    response = api.stream(publish=[foreign, own])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
    messages = parse_stream(response.text)
    assert [message.event for message in messages] == [
        "stream.ready",
        "handoff.created",
    ]
    assert messages[0].data == {"heartbeat_seconds": 0.1, "lifetime_seconds": 0.35}
    assert messages[1].id == str(own.id)
    assert messages[1].data == {
        "event": "handoff.created",
        "ids": ["handoff_1234abcd"],
        "occurred_at": int(own.occurred_at),
    }
    assert response.text.startswith("retry: 3000\n\n")
    assert ": heartbeat\n\n" in response.text


def test_a_reconnect_gets_what_it_missed_first() -> None:
    api = LiveApi()
    seen = make_event(api.business.id)
    missed = make_event(api.business.id, LiveEventKind.BOOKING_CHANGED)
    api.bus.publish(seen)
    api.bus.publish(missed)

    messages = parse_stream(api.stream(last_event_id=str(seen.id)).text)

    assert [(message.event, message.id) for message in messages] == [
        ("stream.ready", None),
        ("booking.changed", str(missed.id)),
    ]


def test_an_unknown_or_unreadable_last_event_id_asks_for_a_resync() -> None:
    api = LiveApi()
    for last_event_id in ("01000000000000000-00000000", "not-an-event"):
        messages = parse_stream(api.stream(last_event_id=last_event_id).text)

        assert [message.event for message in messages] == [
            "stream.ready",
            "stream.resync",
        ]


def test_a_blank_last_event_id_is_a_first_connection() -> None:
    messages = parse_stream(LiveApi().stream(last_event_id=" ").text)

    assert [message.event for message in messages] == ["stream.ready"]


def test_owners_and_staff_listen_but_another_business_cannot() -> None:
    api = LiveApi()

    assert api.stream(token=OWNER_TOKEN).status_code == 200
    refused = api.stream(token=OTHER_OWNER_TOKEN)
    assert refused.status_code == 404
    assert refused.json()["error"] == "not_found"
    assert api.client.get(api.url("/events")).status_code == 401


def test_a_person_with_too_many_open_streams_is_asked_to_wait() -> None:
    api = LiveApi()
    for _ in range(2):
        api.streams.open(api.staff_id, api.business.id, None, RecordingSubscriber())

    refused = api.stream(token=STAFF_TOKEN)

    assert refused.status_code == 429
    assert refused.headers["retry-after"] == "30"
    assert api.stream(token=OWNER_TOKEN).status_code == 200


def test_finished_streams_give_their_places_back() -> None:
    api = LiveApi()
    for _ in range(3):
        assert api.stream(token=STAFF_TOKEN).status_code == 200

    assert api.streams.open_stream_count(api.staff_id) == 0
    assert api.streams.open_stream_count(UserId()) == 0


def test_shutting_down_ends_open_streams_at_once() -> None:
    api = LiveApi()

    # The bus closes once the stream has subscribed: an open stream ends.
    messages = parse_stream(api.stream(meanwhile=api.bus.close).text)

    assert [message.event for message in messages] == ["stream.ready"]
