"""
The daily check finds a chain intact, or broken at the first entry that was
changed, removed, put in or cut off; a purge's checkpoint keeps it
verifiable.
"""

from typed_time_provider import Microseconds

from app.adapters.compliance.in_memory_audit_chain_purge_adapter import (
    InMemoryAuditChainPurgeAdapter,
)
from app.schemas.constants.compliance import AuditChainProblem, AuditChainStatus
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditChainPosition,
    AuditPurgeBatchSize,
    AuditRecordCount,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import (
    chain_key_of,
    compute_entry_hash,
)
from tests.compliance.audit_chain.audit_entries import (
    MINUTE,
    START,
    TWO_YEARS_LATER,
    entry,
    wall_clock_at,
)
from tests.compliance.audit_trail_store import AuditTrailStore

BUSINESS: BusinessId = BusinessId()
CHAIN: AuditChainKey = chain_key_of(BUSINESS)
NOW: Microseconds = Microseconds(START + 10_000 * MINUTE)


def written(count: int) -> AuditTrailStore:
    store = AuditTrailStore()
    for minute in range(count):
        store.log.append(entry(BUSINESS, minute))
    return store


def at(store: AuditTrailStore, position: int) -> AuditLogEntryDocument:
    (found,) = [
        stored
        for stored in store.entries.list_all()
        if stored.chain_position == AuditChainPosition(position)
    ]
    return found


def check(
    store: AuditTrailStore,
    previous: AuditChainStatusDocument | None = None,
    max_entries: int = 100_000,
) -> AuditChainStatusDocument:
    return AuditChainVerification(
        store.chains, AuditChainEntryCount(max_entries)
    ).verify(CHAIN, previous, NOW)


def test_an_untouched_chain_is_intact_through_its_newest_entry() -> None:
    store = written(5)

    status = check(store)

    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(5)
    assert status.verified_through_hash == at(store, 5).entry_hash
    assert int(status.entries_checked) == 5
    assert status.resume_position is None


def test_a_changed_entry_is_found() -> None:
    store = written(5)
    tampered = at(store, 3).model_copy(update={"record_count": AuditRecordCount(9)})
    store.entries.upsert(str(tampered.id), tampered)

    status = check(store)

    assert status.status is AuditChainStatus.BROKEN
    assert status.problem is AuditChainProblem.HASH_MISMATCH
    assert status.broken_position == AuditChainPosition(3)


def test_a_changed_entry_with_a_fresh_hash_breaks_the_next_link() -> None:
    store = written(5)
    tampered = at(store, 2).model_copy(update={"record_count": AuditRecordCount(9)})
    tampered = tampered.model_copy(update={"entry_hash": compute_entry_hash(tampered)})
    store.entries.upsert(str(tampered.id), tampered)

    status = check(store)

    assert status.problem is AuditChainProblem.LINK_BROKEN
    assert status.broken_position == AuditChainPosition(3)


def test_a_removed_entry_leaves_a_gap() -> None:
    store = written(5)
    store.entries.delete(str(at(store, 4).id))

    status = check(store)

    assert status.problem is AuditChainProblem.POSITION_GAP
    assert status.broken_position == AuditChainPosition(4)


def test_an_end_cut_off_after_a_check_is_found() -> None:
    store = written(5)
    previous = check(store)
    store.entries.delete(str(at(store, 5).id))

    status = check(store, previous)

    assert status.problem is AuditChainProblem.HEAD_LOST
    assert status.broken_position == AuditChainPosition(5)
    assert status.verified_through_position == AuditChainPosition(5)


def test_a_purge_keeps_the_chain_verifiable() -> None:
    store = written(6)
    previous = check(store)
    purges = InMemoryAuditChainPurgeAdapter(
        store.entries, store.checkpoints, wall_clock_at(TWO_YEARS_LATER)
    )

    removed = purges.purge(
        CHAIN, Microseconds(START + 4 * MINUTE), AuditPurgeBatchSize(100)
    )

    assert int(removed) == 4
    checkpoint = store.chains.checkpoint_of(CHAIN)
    assert checkpoint is not None
    assert checkpoint.through_position == AuditChainPosition(4)
    status = check(store, previous)
    assert status.status is AuditChainStatus.INTACT
    assert int(status.entries_checked) == 2
    store.log.append(entry(BUSINESS, 7))
    assert check(store, status).verified_through_position == AuditChainPosition(7)


def test_a_checkpoint_moved_over_entries_still_there_is_found() -> None:
    store = written(4)
    hidden = at(store, 2)
    assert hidden.entry_hash is not None
    store.checkpoints.upsert(
        str(CHAIN),
        AuditChainCheckpointDocument(
            id=CHAIN,
            business_id=BUSINESS,
            through_position=AuditChainPosition(2),
            through_hash=hidden.entry_hash,
            purged_count=AuditChainEntryCount(2),
            purged_before=Microseconds(START),
        ),
    )

    status = check(store)

    assert status.problem is AuditChainProblem.CHECKPOINT_MISMATCH
    assert status.broken_position == AuditChainPosition(1)


def test_a_long_chain_is_checked_over_several_runs() -> None:
    store = written(1_200)

    first = check(store, max_entries=500)
    second = check(store, first, max_entries=500)
    third = check(store, second, max_entries=500)

    assert first.resume_position == AuditChainPosition(501)
    assert second.resume_position == AuditChainPosition(1_001)
    assert third.resume_position is None
    assert third.status is AuditChainStatus.INTACT
    assert third.verified_through_position == AuditChainPosition(1_200)


def test_an_empty_chain_is_intact() -> None:
    status = check(AuditTrailStore())

    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position is None
    assert int(status.entries_checked) == 0
