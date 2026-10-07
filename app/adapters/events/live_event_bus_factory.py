"""Choose the live event bus for the container wiring."""

from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.adapters.events.live_event_fanout import LiveEventFanout
from app.adapters.events.postgres_live_event_bus_adapter import (
    PostgresLiveEventBusAdapter,
)
from app.adapters.events.postgres_live_event_listener import (
    PostgresLiveEventListener,
    connect_listener,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.live_events import LiveEventBusAdapterContract
from app.schemas.typings.platform.strings import DatabaseUrl


def build_live_event_bus_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    database_url: DatabaseUrl | None,
    listen_database_url: DatabaseUrl | None,
) -> LiveEventBusAdapterContract:
    """
    Postgres NOTIFY/LISTEN with DATABASE_URL (LISTEN on
    LIVE_EVENTS_DATABASE_URL when set: a direct session, for a DATABASE_URL
    that goes through a transaction pooler), else in memory.
    """

    if connection_pool is None or database_url is None:
        return InMemoryLiveEventBusAdapter()

    listen_url: DatabaseUrl = listen_database_url or database_url
    fanout = LiveEventFanout()
    listener = PostgresLiveEventListener(
        connect=lambda: connect_listener(listen_url),
        fanout=fanout,
    )
    return PostgresLiveEventBusAdapter(connection_pool, listener, fanout)
