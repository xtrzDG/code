"""
Live events between API processes through Postgres NOTIFY/LISTEN: a change
published by one process (or the worker) reaches the streams of another.
"""

import pytest

from app.adapters.events.live_event_bus_factory import build_live_event_bus_adapter
from app.adapters.events.live_event_fanout import LiveEventFanout
from app.adapters.events.postgres_live_event_bus_adapter import (
    PostgresLiveEventBusAdapter,
)
from app.adapters.events.postgres_live_event_listener import (
    LISTENER_APPLICATION_NAME,
    LIVE_EVENTS_CHANNEL,
    PostgresLiveEventListener,
    connect_listener,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from tests.live_events.live_event_builders import RecordingSubscriber, make_event
from tests.storage.live_event_buses import (
    LISTEN_TIMEOUT_SECONDS,
    process_bus,
    wait_until,
)
from tests.storage.postgres_server import ThrowawayPostgresServer


def test_an_event_published_by_one_process_reaches_the_streams_of_another(
    database_url: DatabaseUrl,
) -> None:
    business_id = BusinessId()
    with process_bus(database_url) as publisher, process_bus(database_url) as api:
        stream, foreign = RecordingSubscriber(), RecordingSubscriber()
        api.bus.subscribe(business_id, stream)
        api.bus.subscribe(BusinessId(), foreign)
        assert api.listener.wait_until_listening(LISTEN_TIMEOUT_SECONDS)

        seen = make_event(
            business_id, LiveEventKind.HANDOFF_CREATED, "handoff_1234abcd"
        )
        missed = make_event(business_id, LiveEventKind.BOOKING_CREATED)
        publisher.bus.publish(seen)
        publisher.bus.publish(missed)

        assert wait_until(lambda: len(stream.events) == 2)
        assert stream.events == [seen, missed]
        assert foreign.events == []
        # The receiving process keeps them for reconnecting cabinets; the
        # publishing one never listened (worker processes never do).
        assert api.bus.replay_after(business_id, seen.id) == [missed]
        assert publisher.bus.replay_after(business_id, seen.id) is None


def test_a_lost_listen_session_comes_back_and_asks_streams_to_resync(
    database_url: DatabaseUrl,
    postgres_server: ThrowawayPostgresServer,
    database_name: str,
) -> None:
    business_id = BusinessId()
    with process_bus(database_url) as api:
        stream = RecordingSubscriber()
        api.bus.subscribe(business_id, stream)
        assert api.listener.wait_until_listening(LISTEN_TIMEOUT_SECONDS)
        assert wait_until(lambda: stream.resyncs == 1)

        with postgres_server.admin_connection(database_name) as admin:
            admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where application_name = %s and datname = %s",
                (LISTENER_APPLICATION_NAME, database_name),
            )

        assert wait_until(lambda: stream.resyncs == 2)
        assert api.listener.wait_until_listening(LISTEN_TIMEOUT_SECONDS)
        event = make_event(business_id)
        api.bus.publish(event)
        assert wait_until(lambda: stream.events == [event])


def test_a_malformed_notification_is_ignored(database_url: DatabaseUrl) -> None:
    business_id = BusinessId()
    with process_bus(database_url) as api:
        stream = RecordingSubscriber()
        api.bus.subscribe(business_id, stream)
        assert api.listener.wait_until_listening(LISTEN_TIMEOUT_SECONDS)
        with api.pool.connection() as connection:
            connection.execute(
                "select pg_notify(%s, %s)", (LIVE_EVENTS_CHANNEL, "not json")
            )

        event = make_event(business_id)
        api.bus.publish(event)

        assert wait_until(lambda: stream.events == [event])


def test_publishing_without_a_database_fails_as_a_provider_error() -> None:
    unreachable = DatabaseUrl("postgresql://nobody@127.0.0.1:1/none")
    pool = PostgresConnectionPoolClient(
        unreachable, max_size=1, connect_timeout_seconds=1
    )
    fanout = LiveEventFanout()
    listener = PostgresLiveEventListener(
        connect=lambda: connect_listener(unreachable), fanout=fanout
    )
    bus = PostgresLiveEventBusAdapter(pool, listener, fanout)
    try:
        with pytest.raises(ExternalServiceError):
            bus.publish(make_event(BusinessId()))
    finally:
        bus.close()
        pool.close()


def test_with_a_database_the_bus_goes_through_postgres(
    connection_pool: PostgresConnectionPoolClient,
    database_url: DatabaseUrl,
) -> None:
    bus = build_live_event_bus_adapter(connection_pool, database_url, None)
    try:
        assert isinstance(bus, PostgresLiveEventBusAdapter)
    finally:
        bus.close()
