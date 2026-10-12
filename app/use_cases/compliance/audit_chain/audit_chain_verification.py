"""
Checking one hash chain of the audit log.

A check walks the chain by position from its start (the first position, or
the one after a purge checkpoint), a page at a time, and finds it BROKEN at
the first entry that is not where it should be (POSITION_GAP), does not
name the hash of the entry before it (LINK_BROKEN) or no longer hashes to
its own hash (HASH_MISMATCH). Before that it looks for the newest entry an
earlier check verified: an end of the chain cut off or rewritten from
there on would otherwise pass (HEAD_LOST); and entries a checkpoint says a
purge removed must be gone (CHECKPOINT_MISMATCH).

A long chain is checked over several runs: one run reads at most
`max_entries` entries and the next goes on from `resume_position`, after
the entry it verified last.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.schemas.constants.compliance import AuditChainProblem, AuditChainStatus
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
)
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
    business_of_chain,
    compute_entry_hash,
)

PAGE_SIZE: DocumentQueryLimit = DocumentQueryLimit(500)
ONE: DocumentQueryLimit = DocumentQueryLimit(1)
MAX_ENTRIES_PER_RUN: int = 100_000


@dataclass(frozen=True)
class ChainFinding:
    """The first problem a check met, and where."""

    problem: AuditChainProblem
    position: AuditChainPosition


@dataclass
class ChainWalk:
    """Where a walk stands: the next position, the hash it must name."""

    position: AuditChainPosition
    expected_prev: AuditEntryHash
    checked: int = 0
    last: AuditLogEntryDocument | None = None
    reached_head: bool = False


class AuditChainVerification:
    """Checks one chain and returns what the check found."""

    def __init__(
        self,
        chain_repo: AuditChainRepoContract,
        max_entries: int = MAX_ENTRIES_PER_RUN,
    ) -> None:
        self._chain_repo: AuditChainRepoContract = chain_repo
        self._max_entries: int = max_entries

    def verify(
        self,
        chain_key: AuditChainKey,
        previous: AuditChainStatusDocument | None,
        now: Microseconds,
    ) -> AuditChainStatusDocument:
        """What a check of the chain finds, given what the last one found."""

        checkpoint: AuditChainCheckpointDocument | None = (
            self._chain_repo.checkpoint_of(chain_key)
        )
        start = ChainWalk(
            position=(
                FIRST_POSITION
                if checkpoint is None
                else AuditChainPosition(int(checkpoint.through_position) + 1)
            ),
            expected_prev=(
                GENESIS_HASH if checkpoint is None else checkpoint.through_hash
            ),
        )
        finding: ChainFinding | None = self._find_lost_entries(
            chain_key, checkpoint, previous, start.position
        )
        walk: ChainWalk = start
        if finding is None:
            walk = self._resumed(chain_key, previous, start)
            finding = self._walk(chain_key, walk)

        return self._status(chain_key, previous, walk, finding, now)

    def _find_lost_entries(
        self,
        chain_key: AuditChainKey,
        checkpoint: AuditChainCheckpointDocument | None,
        previous: AuditChainStatusDocument | None,
        start: AuditChainPosition,
    ) -> ChainFinding | None:
        """Entries a checkpoint says are gone, or a verified end that is."""

        if checkpoint is not None:
            oldest: list[AuditLogEntryDocument] = self._chain_repo.entries_from(
                chain_key, FIRST_POSITION, ONE
            )
            if oldest and int(oldest[0].chain_position or 0) < int(start):
                return ChainFinding(
                    AuditChainProblem.CHECKPOINT_MISMATCH,
                    oldest[0].chain_position or FIRST_POSITION,
                )

        if (
            previous is None
            or previous.verified_through_position is None
            or int(previous.verified_through_position) < int(start)
        ):
            return None

        anchor: AuditChainPosition = previous.verified_through_position
        found: list[AuditLogEntryDocument] = self._chain_repo.entries_from(
            chain_key, anchor, ONE
        )
        if (
            not found
            or found[0].chain_position != anchor
            or found[0].entry_hash != previous.verified_through_hash
        ):
            return ChainFinding(AuditChainProblem.HEAD_LOST, anchor)

        return None

    def _resumed(
        self,
        chain_key: AuditChainKey,
        previous: AuditChainStatusDocument | None,
        start: ChainWalk,
    ) -> ChainWalk:
        """Go on after the entry the last run verified, if it stopped early."""

        if (
            previous is None
            or previous.status is not AuditChainStatus.INTACT
            or previous.resume_position is None
            or int(previous.resume_position) <= int(start.position)
        ):
            return start

        before = AuditChainPosition(int(previous.resume_position) - 1)
        found: list[AuditLogEntryDocument] = self._chain_repo.entries_from(
            chain_key, before, ONE
        )
        if (
            not found
            or found[0].chain_position != before
            or found[0].entry_hash is None
        ):
            return start

        return ChainWalk(
            position=previous.resume_position, expected_prev=found[0].entry_hash
        )

    def _walk(self, chain_key: AuditChainKey, walk: ChainWalk) -> ChainFinding | None:
        while walk.checked < self._max_entries:
            page: list[AuditLogEntryDocument] = self._chain_repo.entries_from(
                chain_key, walk.position, PAGE_SIZE
            )
            for entry in page:
                finding: ChainFinding | None = check_entry(entry, walk)
                if finding is not None:
                    return finding

                walk.expected_prev = entry.entry_hash or GENESIS_HASH
                walk.position = AuditChainPosition(int(walk.position) + 1)
                walk.checked += 1
                walk.last = entry

            if len(page) < int(PAGE_SIZE):
                walk.reached_head = True
                return None

        return None

    def _status(
        self,
        chain_key: AuditChainKey,
        previous: AuditChainStatusDocument | None,
        walk: ChainWalk,
        finding: ChainFinding | None,
        now: Microseconds,
    ) -> AuditChainStatusDocument:
        through_position = (
            None if previous is None else previous.verified_through_position
        )
        through_hash = None if previous is None else previous.verified_through_hash
        if (
            finding is None
            and walk.last is not None
            and (
                through_position is None
                or int(walk.last.chain_position or 0) >= int(through_position)
            )
        ):
            through_position = walk.last.chain_position
            through_hash = walk.last.entry_hash

        return AuditChainStatusDocument(
            id=chain_key,
            business_id=business_of_chain(chain_key),
            status=(
                AuditChainStatus.INTACT if finding is None else AuditChainStatus.BROKEN
            ),
            problem=None if finding is None else finding.problem,
            broken_position=None if finding is None else finding.position,
            verified_through_position=through_position,
            verified_through_hash=through_hash,
            resume_position=(
                None if finding is not None or walk.reached_head else walk.position
            ),
            entries_checked=AuditChainEntryCount(walk.checked),
            checked_at=now,
            created_at=now if previous is None else previous.created_at,
            updated_at=now,
        )


def check_entry(entry: AuditLogEntryDocument, walk: ChainWalk) -> ChainFinding | None:
    """The problem of the entry the walk expects next, if any."""

    if entry.chain_position != walk.position:
        return ChainFinding(AuditChainProblem.POSITION_GAP, walk.position)

    if entry.prev_hash != walk.expected_prev:
        return ChainFinding(AuditChainProblem.LINK_BROKEN, walk.position)

    if entry.entry_hash != compute_entry_hash(entry):
        return ChainFinding(AuditChainProblem.HASH_MISMATCH, walk.position)

    return None
