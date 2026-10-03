"""Choose the job queue's wake-up signal for the container wiring."""

from app.adapters.jobs.postgres_job_wakeup_adapter import (
    PostgresJobWakeupAdapter,
    connect_wakeup_listener,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.jobs import JobWakeupContract
from app.schemas.typings.platform.strings import DatabaseUrl
from app.utilities.jobs.job_wakeup_signal import JobWakeupSignal


def build_job_wakeup_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    database_url: DatabaseUrl | None,
    listen_database_url: DatabaseUrl | None,
) -> JobWakeupContract:
    """
    Postgres NOTIFY/LISTEN with DATABASE_URL (the worker listens on
    LIVE_EVENTS_DATABASE_URL when set: a direct session, for a DATABASE_URL
    that goes through a transaction pooler), else the in-process signal
    (without a database the API and its embedded worker share one process).
    """

    if connection_pool is None or database_url is None:
        return JobWakeupSignal()

    listen_url: DatabaseUrl = listen_database_url or database_url
    return PostgresJobWakeupAdapter(
        connection_pool=connection_pool,
        connect=lambda: connect_wakeup_listener(listen_url),
    )
