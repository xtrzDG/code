"""One storage transaction for a block of code: the unit of work."""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg

from app.adapters.storage.postgres.postgres_session_settings import (
    apply_storage_scope,
    translate_storage_error,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.storage import StorageScopeContract, StorageUnitOfWorkContract

UNIT_OF_WORK_LABEL: str = "unit of work"


class PostgresUnitOfWorkAdapter(StorageUnitOfWorkContract):
    """
    A unit of work on Postgres: the block pins one connection of the pool
    (`pinned_connection`), opens one transaction on it and applies the row
    level security scope of the running code once, at the start.

    Every storage operation of the same thread inside the block runs on
    that connection as a savepoint of the unit: it sets the scope it needs
    itself (a document collection its scope, platform tables the platform
    scope), so a platform-wide write of the unit never leaves the bypass on
    for the tenant write after it, and its error rolls back only itself.
    The block's writes commit together when it ends, or roll back together
    when it raises; the transaction-scoped advisory locks taken inside end
    with it. A unit inside a unit is a savepoint of the outer one.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContract,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._storage_scope: StorageScopeContract = storage_scope

    @contextmanager
    def unit_of_work(self) -> Generator[None]:
        try:
            with (
                self._connection_pool.pinned_connection() as connection,
                connection.transaction(),
            ):
                apply_storage_scope(connection, self._storage_scope.current())
                yield
        except psycopg.Error as error:
            application_error = translate_storage_error(error, UNIT_OF_WORK_LABEL)
            if application_error is None:
                raise

            raise application_error from error
