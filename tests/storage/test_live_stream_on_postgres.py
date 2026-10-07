"""
The live stream on Postgres: a booking made through one API process reaches
the cabinet's stream on another (NOTIFY on a pooled connection, LISTEN on
the other process's session), and another business cannot listen in.
"""

from app.schemas.dto.live_events import LiveStreamLimits
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamLifetimeSeconds,
)
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.live_events.live_api import OTHER_OWNER_TOKEN, TEST_LIMITS, LiveApi
from tests.live_events.live_bookings import book_while_listening, publish_changes_on
from tests.storage.live_event_buses import (
    LISTEN_TIMEOUT_SECONDS,
    ProcessBus,
    process_bus,
)

# A booking through Postgres and NOTIFY to another process's LISTEN session
# can take longer than the in-memory tests' stream lives on a busy machine:
# these streams stay open long enough for it.
POSTGRES_LIMITS: LiveStreamLimits = TEST_LIMITS.model_copy(
    update={"lifetime_seconds": LiveStreamLifetimeSeconds(3.0)}
)


def listening_api(api_process: ProcessBus) -> LiveApi:
    api = LiveApi(limits=POSTGRES_LIMITS, bus=api_process.bus)
    return api


def test_the_stream_receives_a_booking_made_through_another_process(
    database_url: DatabaseUrl,
) -> None:
    with process_bus(database_url) as worker, process_bus(database_url) as api_process:
        api = listening_api(api_process)
        publish_changes_on(api, worker.bus)
        # The first stream starts the process's LISTEN session; make sure it
        # listens before the booking is made.
        api.stream()
        assert api_process.listener.wait_until_listening(LISTEN_TIMEOUT_SECONDS)

        names, _ = book_while_listening(api)

    assert names == ["stream.ready", "booking.created"]


def test_another_business_cannot_listen_on_postgres(database_url: DatabaseUrl) -> None:
    with process_bus(database_url) as api_process:
        api = listening_api(api_process)

        assert api.stream(token=OTHER_OWNER_TOKEN).status_code == 404
