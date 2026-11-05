"""
What the API's lifespan and the worker's main share around serving: the
startup heap settled once the process has warmed up (GC_FREEZE_AFTER_WARMUP,
GC_THRESHOLDS; docs/operations/capacity.md) and, on the way out, given back
together with the Postgres pools.
"""

from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.containers.app import AppContainer


def settle_startup_heap(app_container: AppContainer) -> None:
    """
    The process has built its container and run its startup steps and
    serves next: its startup heap leaves the collector's generations now,
    before any request or job waits behind a collection of it.
    """

    app_container.utilities.startup_heap_tuner().settle_after_warmup()


def release_process_resources(app_container: AppContainer) -> None:
    """Close the Postgres pools; give the frozen heap back to the collector."""

    connection_pools: PostgresConnectionPools | None = (
        app_container.clients.postgres_pools()
    )
    if connection_pools is not None:
        connection_pools.close()

    app_container.utilities.startup_heap_tuner().release()
