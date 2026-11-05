"""
One walk along an audit hash chain: entries by position, a page at a time,
each checked against the one before it.

The walk stops at the first entry that is not where it should be
(POSITION_GAP), does not name the hash of the entry before it
(LINK_BROKEN) or no longer hashes to its own hash (HASH_MISMATCH), at the
chain's newest entry, or once it has read `max_entries`.
"""

from dataclasses import dataclass

from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.schemas.constants.compliance import AuditChainProblem
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditChainPosition,
)
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.utilities.compliance.audit_chain_hashing import (
    FIRST_POSITION,
    GENESIS_HASH,
    compute_entry_hash,
    position_after,
)

PAGE_SIZE: DocumentQueryLimit = DocumentQueryLimit(500)


@dataclass(frozen=True)
class ChainFinding:
    """The first problem a check met, and where."""

    problem: AuditChainProblem
    position: AuditChainPosition


@dataclass
class ChainWalk:
    """
    Where a walk stands: the position it began at, the next position and
    the hash the entry there must name, the last entry it verified.
    """

    start: AuditChainPosition
    position: AuditChainPosition
    expected_prev: AuditEntryHash
    last: AuditLogEntryDocument | None = None
    reached_head: bool = False

    @property
    def checked(self) -> AuditChainEntryCount:
        """How many entries the walk verified (positions run without gaps)."""

        return AuditChainEntryCount(int(self.position) - int(self.start))


def walk_from_checkpoint(checkpoint: AuditChainCheckpointDocument | None) -> ChainWalk:
    """A walk from the chain's first entry, or from the one after a purge."""

    if checkpoint is None:
        return ChainWalk(
            start=FIRST_POSITION, position=FIRST_POSITION, expected_prev=GENESIS_HASH
        )

    position: AuditChainPosition = position_after(checkpoint.through_position)
    return ChainWalk(
        start=position, position=position, expected_prev=checkpoint.through_hash
    )


def walk_chain(
    chain_repo: AuditChainRepoContract,
    chain_key: AuditChainKey,
    walk: ChainWalk,
    max_entries: AuditChainEntryCount,
) -> ChainFinding | None:
    """Walk on until a problem, the chain's newest entry or `max_entries`."""

    while int(walk.checked) < int(max_entries):
        page: list[AuditLogEntryDocument] = chain_repo.entries_from(
            chain_key, walk.position, PAGE_SIZE
        )
        for entry in page:
            finding: ChainFinding | None = check_entry(entry, walk)
            if finding is not None:
                return finding

            walk.expected_prev = entry.entry_hash or GENESIS_HASH
            walk.position = position_after(walk.position)
            walk.last = entry

        if len(page) < int(PAGE_SIZE):
            walk.reached_head = True
            return None

    return None


def check_entry(entry: AuditLogEntryDocument, walk: ChainWalk) -> ChainFinding | None:
    """The problem of the entry the walk expects next, if any."""

    if entry.chain_position != walk.position:
        return ChainFinding(AuditChainProblem.POSITION_GAP, walk.position)

    if entry.prev_hash != walk.expected_prev:
        return ChainFinding(AuditChainProblem.LINK_BROKEN, walk.position)

    if entry.entry_hash != compute_entry_hash(entry):
        return ChainFinding(AuditChainProblem.HASH_MISMATCH, walk.position)

    return None
