"""
Choose the storage unit of work, the read session and the widget poll's
one-statement read for the container wiring.
"""

from app.adapters.storage.postgres.postgres_read_session_adapter import (
    PostgresReadSessionAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.adapters.storage.postgres.postgres_widget_poll_read_adapter import (
    PostgresWidgetPollReadAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.storage import (
    StorageReadSessionContract,
    StorageScopeContract,
    StorageUnitOfWorkContract,
)
from app.contracts.widget_poll_reads import WidgetPollReadAdapterContract


def build_unit_of_work_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    storage_scope: StorageScopeContract,
) -> StorageUnitOfWorkContract | None:
    """
    One Postgres transaction per block over the shared pool; None without a
    database (in-memory writes have no transaction to group them in).
    """

    if connection_pool is None:
        return None

    return PostgresUnitOfWorkAdapter(connection_pool, storage_scope)


def build_read_session_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
) -> StorageReadSessionContract | None:
    """
    Several reads in one Postgres transaction; None without a database
    (in-memory reads have no round trips to save).
    """

    if connection_pool is None:
        return None

    return PostgresReadSessionAdapter(connection_pool)


def build_widget_poll_read_adapter(
    connection_pool: PostgresConnectionPoolClient | None,
    storage_scope: StorageScopeContract,
) -> WidgetPollReadAdapterContract | None:
    """
    A widget poll's reads in one statement (Postgres); None without a
    database (the poll reads through its repositories: in memory there are
    no round trips to save).
    """

    if connection_pool is None:
        return None

    return PostgresWidgetPollReadAdapter(connection_pool, storage_scope)
