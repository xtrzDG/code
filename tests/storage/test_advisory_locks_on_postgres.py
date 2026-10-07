"""
Postgres advisory locks between two pools (two processes' sessions): one
holder at a time, writes committed before the next holder reads, bounded
waits, and a lock never left behind on a pooled connection.
"""

import threading
import time
from collections.abc import Generator
from dataclasses import dataclass

import pytest

from app.adapters.locks.postgres_advisory_lock_adapter import (
    PostgresAdvisoryLockAdapter,
)
from app.adapters.storage.postgres.postgres_unit_of_work_adapter import (
    PostgresUnitOfWorkAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.domain.contacts import ContactDocument
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.builders import build_contact
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.rls_contacts import GEORGIA
from tests.storage.storage_testing import build_fixed_wall_clock

KEY: AdvisoryLockKey = AdvisoryLockKey("bookings|biz_test")
WAIT: LockWaitSeconds = LockWaitSeconds(20)
# A held lock is let go by the test; this only bounds a broken test.
HELD_SECONDS: float = 10.0
# How long a waiter is watched to still wait (it cannot get a held lock).
QUIET_SECONDS: float = 0.3
PAST_STATEMENT_TIMEOUT_SECONDS: float = 1.5


@dataclass
class Taker:
    """A thread waiting for KEY: whether it got it, and what refused it."""

    taken: threading.Event
    errors: list[ExternalServiceError]
    thread: threading.Thread | None = None

    def join(self) -> None:
        if self.thread is not None:
            self.thread.join(HELD_SECONDS)


class LockingProcess:
    """What one API process has: a pool, a scope, locks and contacts."""

    def __init__(
        self,
        database_url: DatabaseUrl,
        statement_timeout_seconds: int | None = None,
    ) -> None:
        self.pool = PostgresConnectionPoolClient(
            database_url,
            max_size=4,
            statement_timeout_seconds=statement_timeout_seconds,
        )
        self.scope = StorageScopeContext()
        self.locks = PostgresAdvisoryLockAdapter(
            self.pool, PostgresUnitOfWorkAdapter(self.pool, self.scope)
        )
        self.contacts: DocumentCollectionAdapterContract[ContactDocument] = (
            PostgresCollectionFactory(
                connection_pool=self.pool,
                storage_scope=self.scope,
                wall_clock=build_fixed_wall_clock(),
            )(ContactDocument, "contacts")
        )

    def is_key_free(self) -> bool:
        """Whether another session could take the key right now."""

        with self.pool.connection() as connection:
            row = connection.execute(
                "select pg_try_advisory_lock(hashtextextended(%s, 0))", (str(KEY),)
            ).fetchone()
            assert row is not None
            if row[0] is True:
                connection.execute(
                    "select pg_advisory_unlock(hashtextextended(%s, 0))", (str(KEY),)
                )

        return row[0] is True


@pytest.fixture
def processes(database_url: DatabaseUrl) -> Generator[tuple[LockingProcess, ...]]:
    first, second = LockingProcess(database_url), LockingProcess(database_url)
    try:
        yield first, second
    finally:
        first.pool.close()
        second.pool.close()


def hold_in_thread(
    process: LockingProcess,
    release: threading.Event,
    is_session: bool = False,
) -> threading.Thread:
    """Hold KEY in a thread until `release` is set; return once it holds."""

    holding = threading.Event()

    def hold() -> None:
        lock = (
            process.locks.hold_with_session(KEY, WAIT)
            if is_session
            else process.locks.hold_with_transaction(KEY, WAIT)
        )
        with lock:
            holding.set()
            release.wait(HELD_SECONDS)

    thread = threading.Thread(target=hold)
    thread.start()
    assert holding.wait(HELD_SECONDS)
    return thread


def take_in_thread(process: LockingProcess, is_session: bool = False) -> Taker:
    """Wait for KEY in a thread; `taken` is set once it got the lock."""

    taker = Taker(threading.Event(), [])

    def take() -> None:
        lock = (
            process.locks.hold_with_session(KEY, WAIT)
            if is_session
            else process.locks.hold_with_transaction(KEY, WAIT)
        )
        try:
            with lock:
                taker.taken.set()
        except ExternalServiceError as error:
            taker.errors.append(error)

    taker.thread = threading.Thread(target=take)
    taker.thread.start()
    return taker


def test_a_transaction_lock_has_one_holder_across_processes(
    processes: tuple[LockingProcess, ...],
) -> None:
    first, second = processes
    release = threading.Event()
    holder = hold_in_thread(first, release)

    taker = take_in_thread(second)
    # While the first process holds the lock, the second one waits for it.
    assert not taker.taken.wait(QUIET_SECONDS)
    release.set()

    assert taker.taken.wait(HELD_SECONDS)
    holder.join(HELD_SECONDS)
    taker.join()
    assert taker.errors == []


def test_the_next_holder_reads_what_the_previous_one_wrote(
    processes: tuple[LockingProcess, ...],
) -> None:
    first, second = processes
    business_id = BusinessId()
    contact = build_contact(GEORGIA, business_id)
    written, release = threading.Event(), threading.Event()

    def write_under_the_lock() -> None:
        with (
            first.scope.scoped_to_business(business_id),
            first.locks.hold_with_transaction(KEY, WAIT),
        ):
            first.contacts.upsert(str(contact.id), contact)
            written.set()
            release.wait(HELD_SECONDS)

    writer = threading.Thread(target=write_under_the_lock)
    writer.start()
    assert written.wait(HELD_SECONDS)
    with second.scope.scoped_to_business(business_id):
        # Not committed yet: the write ends with the lock.
        assert second.contacts.get(str(contact.id)) is None
        release.set()
        with second.locks.hold_with_transaction(KEY, WAIT):
            assert second.contacts.get(str(contact.id)) == contact

    writer.join(HELD_SECONDS)


def test_a_busy_lock_fails_after_its_wait_and_names_no_ids(
    processes: tuple[LockingProcess, ...],
) -> None:
    first, second = processes
    release = threading.Event()
    holder = hold_in_thread(first, release)
    started = time.monotonic()

    # The holder keeps the lock until after the refusal: only the wait's
    # own limit can end it.
    with pytest.raises(ExternalServiceError) as refusal:  # noqa: SIM117
        with second.locks.hold_with_transaction(KEY, LockWaitSeconds(1)):
            pytest.fail("the lock was busy")
    waited = time.monotonic() - started
    release.set()

    holder.join(HELD_SECONDS)
    assert waited >= 0.9
    assert "bookings lock stayed busy for 1 s" in str(refusal.value)
    assert "biz_test" not in str(refusal.value)
    # The failed unit gave its connection back clean.
    assert second.pool.open_connection_count() == second.pool.idle_connection_count()


def test_a_session_lock_spans_committed_writes_on_one_connection(
    processes: tuple[LockingProcess, ...],
) -> None:
    first, second = processes
    business_id = BusinessId()
    contact = build_contact(GEORGIA, business_id)

    with (
        first.scope.scoped_to_business(business_id),
        first.locks.hold_with_session(KEY, WAIT),
    ):
        first.contacts.upsert(str(contact.id), contact)
        with second.scope.scoped_to_business(business_id):
            # Committed at once, while the lock is still held.
            assert second.contacts.get(str(contact.id)) == contact
        assert not second.is_key_free()
        assert first.pool.open_connection_count() == 1

    assert second.is_key_free()


def test_a_session_lock_waits_past_the_statement_timeout(
    database_url: DatabaseUrl,
) -> None:
    first = LockingProcess(database_url)
    second = LockingProcess(database_url, statement_timeout_seconds=1)
    try:
        release = threading.Event()
        holder = hold_in_thread(first, release, is_session=True)
        taker = take_in_thread(second, is_session=True)
        # Still waiting, unrefused, past its sessions' 1 s statement timeout.
        assert not taker.taken.wait(PAST_STATEMENT_TIMEOUT_SECONDS)
        assert taker.errors == []
        release.set()
        assert taker.taken.wait(HELD_SECONDS)
        holder.join(HELD_SECONDS)
        taker.join()
        assert taker.errors == []
        # The wait's limits ended with the short transaction around it.
        with second.pool.connection() as connection:
            row = connection.execute("show statement_timeout").fetchone()
        assert row == ("1s",)
    finally:
        first.pool.close()
        second.pool.close()


def test_a_session_lock_on_a_dead_connection_is_never_pooled_again(
    processes: tuple[LockingProcess, ...],
) -> None:
    first, second = processes

    with first.locks.hold_with_session(KEY, WAIT):
        with first.pool.connection() as connection:
            row = connection.execute("select pg_backend_pid()").fetchone()
        assert row is not None
        with second.pool.connection() as connection:
            # Waits until the backend is gone (or 10 s), not a guessed delay.
            connection.execute("select pg_terminate_backend(%s, 10000)", (row[0],))

    # The server freed the lock with the session; the pool dropped it.
    assert first.pool.open_connection_count() == 0
    assert second.is_key_free()
    with first.locks.hold_with_session(KEY, WAIT):
        assert not second.is_key_free()
