"""An open cabinet hears a booking staff made elsewhere, within its stream."""

from tests.live_events.live_api import LiveApi
from tests.live_events.live_bookings import book_while_listening, publish_changes_on


def test_the_stream_receives_a_booking_made_while_it_is_open() -> None:
    api = LiveApi()
    publish_changes_on(api, api.bus)

    names, _ = book_while_listening(api)

    assert names == ["stream.ready", "booking.created"]
