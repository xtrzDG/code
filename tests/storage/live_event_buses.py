"""Postgres live event buses for tests: one per simulated API process."""

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass

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
from app.schemas.typings.platform.strings import DatabaseUrl

LISTEN_TIMEOUT_SECONDS: float = 10.0
# Short pauses: a lost connection is back within the test's patience.
FIRST_RECONNECT_DELAY_SECONDS: float = 0.05


@dataclass
class ProcessBus:
    """The bus of one API process with its own pool and LISTEN session."""

    bus: PostgresLiveEventBusAdapter
    listener: PostgresLiveEventListener
    pool: PostgresConnectionPoolClient


@contextmanager
def process_bus(database_url: DatabaseUrl) -> Generator[ProcessBus]:
    pool = PostgresConnectionPoolClient(database_url, max_size=2)
    fanout = LiveEventFanout()
    listener = PostgresLiveEventListener(
        connect=lambda: connect_listener(database_url),
        fanout=fanout,
        first_delay_seconds=FIRST_RECONNECT_DELAY_SECONDS,
        max_delay_seconds=FIRST_RECONNECT_DELAY_SECONDS * 4,
    )
    process = ProcessBus(
        PostgresLiveEventBusAdapter(pool, listener, fanout), listener, pool
    )
    try:
        yield process
    finally:
        process.bus.close()
        listener.stop(timeout_seconds=LISTEN_TIMEOUT_SECONDS)
        pool.close()


def wait_until(condition: Callable[[], bool], timeout_seconds: float = 10.0) -> bool:
    deadline: float = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()
