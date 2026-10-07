import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import LiteralString

import psycopg
from psycopg import errors as database_errors

from app.adapters.locks.process_locks import (
    ProcessLocks,
    describe_lock_purpose,
    lock_wait_exceeded,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnection,
    PostgresConnectionPoolClient,
)
from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

LOGGER: logging.Logger = logging.getLogger(__name__)
TRANSACTION_LOCK: LiteralString = (
    "select pg_advisory_xact_lock(hashtextextended(%s, 0))"
)
SESSION_LOCK: LiteralString = "select pg_advisory_lock(hashtextextended(%s, 0))"
SESSION_UNLOCK: LiteralString = "select pg_advisory_unlock(hashtextextended(%s, 0))"
# Both end with the transaction they are set in (is_local => true).
LOCK_WAIT_LIMIT: LiteralString = "select set_config('lock_timeout', %s, true)"
STATEMENT_LIMIT: LiteralString = "select set_config('statement_timeout', %s, true)"
MINIMUM_DATABASE_WAIT_SECONDS: float = 1.0


class PostgresAdvisoryLockAdapter(AdvisoryLockAdapterContract):
    """
    Locks every API instance and worker respects: Postgres advisory locks on
    the 64-bit hash of the key (`hashtextextended(key, 0)`).

    - `hold_with_transaction` runs the block as a unit of work and takes
      `pg_advisory_xact_lock` first: the block's writes and the lock's end
      commit together, so the next holder reads them (bookings of a
      business, the login code send reservations).
    - `hold_with_session` takes `pg_advisory_lock` on a connection pinned
      for the block and frees it at the end (or the server frees it when
      the process dies). The block's own statements run on that connection,
      each in its own transaction, so no transaction stays open across a
      model call (`idle_in_transaction_session_timeout` would end it) and a
      waiting turn holds one connection, not two (customer messages).

    Waiters of one key in this process queue on a process lock first, so a
    burst of one customer's messages holds one database connection, not one
    per message. A wait longer than `wait` (lock_timeout) fails with
    ExternalServiceError instead of hanging.
    """

    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        unit_of_work: StorageUnitOfWorkContract,
        process_locks: ProcessLocks | None = None,
    ) -> None:
        self._connection_pool: PostgresConnectionPoolClient = connection_pool
        self._unit_of_work: StorageUnitOfWorkContract = unit_of_work
        self._process_locks: ProcessLocks = (
            ProcessLocks() if process_locks is None else process_locks
        )

    @contextmanager
    def hold_with_transaction(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> Generator[None]:
        deadline: float = time.monotonic() + int(wait)
        with (
            self._process_locks.held(key, float(int(wait))),
            self._connection_pool.pinned_connection() as connection,
            self._unit_of_work.unit_of_work(),
        ):
            acquire_lock(connection, TRANSACTION_LOCK, key, wait, deadline)
            yield

    @contextmanager
    def hold_with_session(
        self,
        key: AdvisoryLockKey,
        wait: LockWaitSeconds,
    ) -> Generator[None]:
        deadline: float = time.monotonic() + int(wait)
        with (
            self._process_locks.held(key, float(int(wait))),
            self._connection_pool.pinned_connection() as connection,
        ):
            with connection.transaction():
                # The statement limit too: the server's default (seconds)
                # would end a wait for a long turn early.
                connection.execute(STATEMENT_LIMIT, (wait_setting(deadline),))
                acquire_lock(connection, SESSION_LOCK, key, wait, deadline)

            try:
                yield
            finally:
                release_session_lock(connection, key)


def acquire_lock(
    connection: PostgresConnection,
    statement: LiteralString,
    key: AdvisoryLockKey,
    wait: LockWaitSeconds,
    deadline: float,
) -> None:
    """Take the lock, waiting until the deadline (lock_timeout) at most."""

    try:
        connection.execute(LOCK_WAIT_LIMIT, (wait_setting(deadline),))
        connection.execute(statement, (str(key),))
    except (
        database_errors.LockNotAvailable,
        database_errors.QueryCanceled,
    ) as error:
        raise lock_wait_exceeded(key, float(int(wait))) from error


def wait_setting(deadline: float) -> str:
    """The rest of the wait as a Postgres duration ("1500ms"), at least 1 s."""

    remaining: float = max(MINIMUM_DATABASE_WAIT_SECONDS, deadline - time.monotonic())
    return f"{int(remaining * 1000)}ms"


def release_session_lock(connection: PostgresConnection, key: AdvisoryLockKey) -> None:
    """
    Free a session lock. A connection whose lock state is unknown (the
    unlock failed) is closed, so the pool never hands out a connection that
    still holds someone's lock; the server frees the lock with the session.
    """

    try:
        row = connection.execute(SESSION_UNLOCK, (str(key),)).fetchone()
    except psycopg.Error:
        LOGGER.warning(
            "Could not free a %s lock; its connection is closed instead.",
            describe_lock_purpose(key),
            exc_info=True,
        )
        connection.close()
        return

    if row is None or row[0] is not True:
        LOGGER.warning(
            "A %s lock was no longer held when it was freed.",
            describe_lock_purpose(key),
        )
