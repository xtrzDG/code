"""
Purges and the daily check: a purge that commits while the check walks
the chain is no break, a purge of the newest verified entry is accepted
only when its cutoff is past the minimum retention of a year, and a purge
never removes entries of the last year.
"""

import pytest
from typed_time_provider import Microseconds

from app.adapters.compliance.in_memory_audit_chain_purge_adapter import (
    InMemoryAuditChainPurgeAdapter,
)
from app.schemas.constants.compliance import AuditChainProblem, AuditChainStatus
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditChainPosition,
    AuditPurgeBatchSize,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.compliance.audit_chain.audit_chain_verification import (
    AuditChainVerification,
)
from app.utilities.compliance.audit_chain_hashing import chain_key_of
from tests.compliance.audit_chain.audit_entries import (
    MINUTE,
    START,
    TWO_YEARS_LATER,
    entry,
    wall_clock_at,
)
from tests.compliance.audit_chain.purge_mid_check import PurgeBeforeEntryRead
from tests.compliance.audit_trail_store import AuditTrailStore

BUSINESS: BusinessId = BusinessId()
CHAIN: AuditChainKey = chain_key_of(BUSINESS)
LATER: Microseconds = Microseconds(TWO_YEARS_LATER)
BATCH: AuditPurgeBatchSize = AuditPurgeBatchSize(1_000)


def written(count: int, first_minute: int = 0) -> AuditTrailStore:
    store = AuditTrailStore()
    for minute in range(first_minute, first_minute + count):
        store.log.append(entry(BUSINESS, minute))
    return store


def purge_through(store: AuditTrailStore, minute: int) -> None:
    """The operator's purge (two years on) of what was written before `minute`."""

    InMemoryAuditChainPurgeAdapter(
        store.entries, store.checkpoints, wall_clock_at(TWO_YEARS_LATER)
    ).purge(CHAIN, Microseconds(START + minute * MINUTE), BATCH)


def at(store: AuditTrailStore, position: int) -> AuditLogEntryDocument:
    (found,) = store.chains.entries_from(
        CHAIN, AuditChainPosition(position), DocumentQueryLimit(1)
    )
    return found


def test_a_purge_committed_between_two_pages_of_the_walk_is_no_break() -> None:
    store = written(1_200)
    # The walk reads entries 1-500, then the purge of 1-900 commits, then the
    # walk reads on from 501.
    racing = PurgeBeforeEntryRead(
        store.chains, read_number=2, commit_purge=lambda: purge_through(store, 900)
    )

    status = AuditChainVerification(racing).verify(CHAIN, None, LATER)

    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(1_200)
    assert int(status.entries_checked) == 300


def test_a_purge_committed_before_the_head_is_looked_up_is_no_break() -> None:
    store = written(1_000)
    previous = AuditChainVerification(store.chains).verify(CHAIN, None, LATER)
    for minute in range(1_000, 1_200):
        store.log.append(entry(BUSINESS, minute))
    racing = PurgeBeforeEntryRead(
        store.chains, read_number=1, commit_purge=lambda: purge_through(store, 1_000)
    )

    status = AuditChainVerification(racing).verify(CHAIN, previous, LATER)

    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(1_200)


def test_a_removed_entry_the_purge_does_not_explain_is_still_found() -> None:
    store = written(1_200)
    store.entries.delete(str(at(store, 1_100).id))
    racing = PurgeBeforeEntryRead(
        store.chains, read_number=2, commit_purge=lambda: purge_through(store, 900)
    )

    status = AuditChainVerification(racing).verify(CHAIN, None, LATER)

    assert status.problem is AuditChainProblem.POSITION_GAP
    assert status.broken_position == AuditChainPosition(1_100)


def test_the_newest_verified_entry_purged_with_a_fresh_cutoff_is_head_lost() -> None:
    store = written(5)
    previous = AuditChainVerification(store.chains).verify(CHAIN, None, LATER)
    last = at(store, 5)
    assert last.chain_position is not None
    assert last.entry_hash is not None
    # What a purge without the retention floor would leave: the whole chain
    # gone, with a checkpoint whose cutoff is only days old.
    for stored in store.entries.list_all():
        store.entries.delete(str(stored.id))
    store.checkpoints.upsert(
        str(CHAIN),
        AuditChainCheckpointDocument(
            id=CHAIN,
            business_id=BUSINESS,
            through_position=last.chain_position,
            through_hash=last.entry_hash,
            purged_count=AuditChainEntryCount(5),
            purged_before=Microseconds(int(LATER) - 3 * 24 * 60 * MINUTE),
        ),
    )

    status = AuditChainVerification(store.chains).verify(CHAIN, previous, LATER)

    assert status.status is AuditChainStatus.BROKEN
    assert status.problem is AuditChainProblem.HEAD_LOST
    assert status.broken_position == AuditChainPosition(5)


def test_the_newest_verified_entry_purged_after_a_year_is_accepted() -> None:
    store = written(5)
    previous = AuditChainVerification(store.chains).verify(CHAIN, None, LATER)

    purge_through(store, 10)
    status = AuditChainVerification(store.chains).verify(CHAIN, previous, LATER)

    assert store.entries.list_all() == []
    assert status.status is AuditChainStatus.INTACT
    assert status.verified_through_position == AuditChainPosition(5)


def test_a_purge_refuses_a_cutoff_younger_than_a_year() -> None:
    store = written(5)
    a_month_on = wall_clock_at(START + 30 * 24 * 60 * MINUTE)
    purges = InMemoryAuditChainPurgeAdapter(
        store.entries, store.checkpoints, a_month_on
    )

    with pytest.raises(ValidationFailedError, match="at least 365 days"):
        purges.purge(CHAIN, Microseconds(START + 10 * MINUTE), BATCH)

    assert len(store.entries.list_all()) == 5
    assert store.chains.checkpoint_of(CHAIN) is None
