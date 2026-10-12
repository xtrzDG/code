"""
Two processes write one business's audit chain at once on Postgres: the
chain's advisory lock lets one append (read the head, insert the next
entry, commit) at a time, so the chain stays one line, every position
taken once and every link right; only audit entries take that lock.
"""

import threading
from collections.abc import Generator, Sequence

import pytest

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldOrder
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.platform.strings import DatabaseUrl
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import chain_key_of
from app.utilities.storage.document_tenancy import infer_collection_isolation
from tests.compliance.audit_chain.audit_entries import START, entry
from tests.storage.audit_chain_process import AuditProcess
from tests.storage.storage_testing import build_fixed_wall_clock

BUSINESS: BusinessId = BusinessId()
# A held lock is let go by the test; this only bounds a broken test.
HELD_SECONDS: float = 10.0
# How long the second writer is watched to still wait for the lock.
QUIET_SECONDS: float = 0.3
ENTRIES_PER_WRITER: int = 30


class GatedEntries(PostgresDocumentCollectionAdapter[AuditLogEntryDocument]):
    """Stops inside the first head read until the test lets it go."""

    def __init__(self, process: AuditProcess) -> None:
        super().__init__(
            document_type=AuditLogEntryDocument,
            collection_name=DocumentCollectionName("audit_log_entries"),
            connection_pool=process.pool,
            storage_scope=process.scope,
            wall_clock=build_fixed_wall_clock(),
            isolation=infer_collection_isolation(AuditLogEntryDocument),
        )
        self.inside = threading.Event()
        self.release = threading.Event()

    def list_by_fields(
        self,
        matches: Sequence[DocumentFieldMatch],
        order: DocumentFieldOrder | None = None,
        limit: DocumentQueryLimit | None = None,
    ) -> list[AuditLogEntryDocument]:
        found = super().list_by_fields(matches, order, limit)
        if not self.inside.is_set():
            self.inside.set()
            assert self.release.wait(HELD_SECONDS)
        return found


@pytest.fixture
def processes(
    database_url: DatabaseUrl,
) -> Generator[tuple[AuditProcess, AuditProcess]]:
    first, second = AuditProcess(database_url), AuditProcess(database_url)
    try:
        yield first, second
    finally:
        first.close()
        second.close()


def stored_chain(process: AuditProcess) -> list[AuditLogEntryDocument]:
    return process.chains.entries_from(
        chain_key_of(BUSINESS), AuditChainPosition(1), DocumentQueryLimit(1_000)
    )


def test_a_writer_waits_while_another_holds_the_chain(
    processes: tuple[AuditProcess, AuditProcess],
    database_url: DatabaseUrl,
) -> None:
    first, second = processes
    gated = GatedEntries(first)
    holder = AuditProcess(database_url, entries=gated)
    first_entry, second_entry = entry(BUSINESS, 0), entry(BUSINESS, 1)
    second_done = threading.Event()

    def write_second() -> None:
        second.log.append(second_entry)
        second_done.set()

    holding = threading.Thread(target=holder.log.append, args=(first_entry,))
    waiting = threading.Thread(target=write_second)
    try:
        holding.start()
        assert gated.inside.wait(HELD_SECONDS)
        waiting.start()
        assert not second_done.wait(QUIET_SECONDS), "it wrote inside another's turn"
        gated.release.set()
        holding.join(HELD_SECONDS)
        waiting.join(HELD_SECONDS)
    finally:
        gated.release.set()
        holder.close()

    chain = stored_chain(second)
    assert [stored.id for stored in chain] == [first_entry.id, second_entry.id]
    assert chain[1].prev_hash == chain[0].entry_hash


def test_two_processes_keep_one_business_chain_in_one_line(
    processes: tuple[AuditProcess, AuditProcess],
) -> None:
    start = threading.Barrier(2)
    failures: list[BaseException] = []

    def write(process: AuditProcess, offset: int) -> None:
        start.wait(HELD_SECONDS)
        try:
            for index in range(ENTRIES_PER_WRITER):
                process.log.append(entry(BUSINESS, offset + index / 100))
        except BaseException as error:  # noqa: BLE001 - reported below
            failures.append(error)

    threads = [
        threading.Thread(target=write, args=(process, offset))
        for offset, process in enumerate(processes)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(HELD_SECONDS * 3)

    assert failures == []
    chain = stored_chain(processes[0])
    assert [int(stored.chain_position or 0) for stored in chain] == list(
        range(1, 2 * ENTRIES_PER_WRITER + 1)
    )
    status = AuditChainVerification(processes[1].chains).verify(
        chain_key_of(BUSINESS), None, build_fixed_wall_clock().now_unix()
    )
    assert status.status is AuditChainStatus.INTACT
    assert int(status.entries_checked) == 2 * ENTRIES_PER_WRITER
    assert int(chain[0].created_at) >= START
