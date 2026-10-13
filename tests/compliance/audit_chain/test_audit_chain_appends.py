"""
Every audit entry joins its chain: its business's, or the platform's when
it names no business, at the next position, linked to the hash of the one
before; and the repository never changes or deletes a stored entry.
"""

import threading

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditChainPosition,
)
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.compliance.audit_chain_hashing import (
    GENESIS_HASH,
    PLATFORM_CHAIN_KEY,
    chain_key_of,
    compute_entry_hash,
)
from tests.compliance.audit_chain.append_only_collection import (
    AppendOnlyCollection,
)
from tests.compliance.audit_chain.audit_entries import START, entry
from tests.compliance.audit_repositories import audit_log_repository
from tests.compliance.audit_trail_store import AuditTrailStore

BUSINESS: BusinessId = BusinessId()
OTHER: BusinessId = BusinessId()
WRITERS: int = 4
ENTRIES_PER_WRITER: int = 25


def chain_of(
    store: AuditTrailStore, chain_key: AuditChainKey
) -> list[AuditLogEntryDocument]:
    return sorted(
        (
            stored
            for stored in store.entries.list_all()
            if stored.chain_key == chain_key
        ),
        key=lambda stored: int(stored.chain_position or 0),
    )


def assert_linked(chain: list[AuditLogEntryDocument], first: int = 1) -> None:
    expected_prev: AuditEntryHash = GENESIS_HASH
    for offset, stored in enumerate(chain):
        assert stored.chain_position == AuditChainPosition(first + offset)
        if offset:
            assert stored.prev_hash == expected_prev
        assert stored.entry_hash == compute_entry_hash(stored)
        assert stored.entry_hash is not None
        expected_prev = stored.entry_hash


def test_entries_are_linked_in_order_in_their_business_chain() -> None:
    store = AuditTrailStore()
    for minute in range(3):
        store.log.append(entry(BUSINESS, minute))
    store.log.append(entry(OTHER, 1))

    chain = chain_of(store, chain_key_of(BUSINESS))
    assert_linked(chain)
    assert chain[0].prev_hash == GENESIS_HASH
    assert [int(stored.created_at) for stored in chain] == [
        START + minute * 60_000_000 for minute in range(3)
    ]
    other = chain_of(store, chain_key_of(OTHER))
    assert [int(stored.chain_position or 0) for stored in other] == [1]


def test_the_chains_head_follows_every_append() -> None:
    store = AuditTrailStore()
    for minute in range(3):
        store.log.append(entry(BUSINESS, minute))

    head = store.heads.get(str(chain_key_of(BUSINESS)))
    newest = chain_of(store, chain_key_of(BUSINESS))[-1]
    assert head is not None
    assert (head.head_position, head.head_hash) == (
        newest.chain_position,
        newest.entry_hash,
    )
    assert head.business_id == BUSINESS
    assert (int(head.created_at), int(head.updated_at)) == (
        START,
        START + 2 * 60_000_000,
    )


def test_entries_without_a_business_are_in_the_platform_chain() -> None:
    store = AuditTrailStore()
    store.log.append(entry(None, action=AuditAction.LOGIN, entity="user"))
    store.log.append(entry(None, 1, action=AuditAction.MFA_CHANGED, entity="user"))

    chain = chain_of(store, PLATFORM_CHAIN_KEY)
    assert len(chain) == 2
    assert_linked(chain)
    assert all(stored.business_id is None for stored in chain)


def test_the_same_entry_twice_is_refused() -> None:
    store = AuditTrailStore()
    first = entry(BUSINESS)
    store.log.append(first)

    with pytest.raises(ConflictError):
        store.log.append(first)
    assert len(chain_of(store, chain_key_of(BUSINESS))) == 1


def test_the_repository_never_changes_a_stored_entry() -> None:
    entries = AppendOnlyCollection()
    log = audit_log_repository(entries)
    for first_minute in (0, 1, 2):
        log.append(
            entry(BUSINESS, first_minute, action=AuditAction.VIEW, actor=UserId())
        )
    owner = UserId()
    for minute in (3, 3.5, 4):  # Repeated identical views are counted beside.
        log.append(entry(BUSINESS, minute, action=AuditAction.VIEW, actor=owner))

    assert entries.inserted == 4


def test_a_chain_emptied_by_a_purge_goes_on_after_its_checkpoint() -> None:
    store = AuditTrailStore()
    chain_key = chain_key_of(BUSINESS)
    last_purged = AuditEntryHash("ab" * 32)
    store.checkpoints.upsert(
        str(chain_key),
        AuditChainCheckpointDocument(
            id=chain_key,
            business_id=BUSINESS,
            through_position=AuditChainPosition(41),
            through_hash=last_purged,
            purged_count=AuditChainEntryCount(41),
            purged_before=Microseconds(START),
        ),
    )

    store.log.append(entry(BUSINESS))

    (stored,) = chain_of(store, chain_key)
    assert stored.chain_position == AuditChainPosition(42)
    assert stored.prev_hash == last_purged


def test_parallel_writers_of_one_business_never_share_a_position() -> None:
    store = AuditTrailStore()
    start = threading.Barrier(WRITERS)

    def write(writer: int) -> None:
        start.wait()
        for index in range(ENTRIES_PER_WRITER):
            store.log.append(entry(BUSINESS, writer + index / 100))

    threads = [
        threading.Thread(target=write, args=(writer,)) for writer in range(WRITERS)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    chain = chain_of(store, chain_key_of(BUSINESS))
    assert len(chain) == WRITERS * ENTRIES_PER_WRITER
    assert_linked(chain)
