"""
Checking one hash chain of the audit log.

A check walks the chain by position from its start (the first position, or
the one after a purge checkpoint), a page at a time (`audit_chain_walk.py`),
and finds it BROKEN at the first entry that is not where it should be,
does not link to the entry before it or no longer hashes to its own hash.
Before that it looks for the newest entry an earlier check verified: an
end of the chain cut off or rewritten from there on would otherwise pass
(HEAD_LOST). A purge may remove that entry only when its cutoff is older
than the minimum retention (`audit_retention.py`). Entries a checkpoint
says a purge removed must be gone (CHECKPOINT_MISMATCH).

A purge may commit while a check walks the chain (the operator's
`workshop purge-audit-log` and the daily job do not wait for each other):
the walk then meets a gap where removed entries were. Each purge moves
the checkpoint in the transaction that removes the entries, so a check
that found a problem reads the checkpoint again; when it moved on, the
check runs again from it, and only a problem the latest checkpoint does
not explain is reported.

A long chain is checked over several runs: one run reads at most
`max_entries` entries and the next goes on from `resume_position`, after
the entry it verified last.
"""

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
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.compliance.audit_chain.audit_chain_status import chain_status
from app.use_cases.compliance.audit_chain.audit_chain_walk import (
    ChainFinding,
    ChainWalk,
    walk_chain,
    walk_from_checkpoint,
)
from app.utilities.compliance.audit_chain_hashing import (
    FIRST_POSITION,
    position_before,
)
from app.utilities.compliance.audit_retention import is_cutoff_allowed

ONE: DocumentQueryLimit = DocumentQueryLimit(1)
MAX_ENTRIES_PER_RUN: AuditChainEntryCount = AuditChainEntryCount(100_000)
# How often one check starts again after purges that committed while it
# walked: a purge removes at most 10 000 entries a statement, so a run over
# a million entries stays well below this.
MAX_CHECKPOINT_MOVES: int = 1_000


class AuditChainVerification:
    """Checks one chain and returns what the check found."""

    def __init__(
        self,
        chain_repo: AuditChainRepoContract,
        max_entries: AuditChainEntryCount = MAX_ENTRIES_PER_RUN,
    ) -> None:
        self._chain_repo: AuditChainRepoContract = chain_repo
        self._max_entries: AuditChainEntryCount = max_entries

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
        status: AuditChainStatusDocument = self._check(
            chain_key, checkpoint, previous, now
        )
        moves: int = 0
        while status.status is AuditChainStatus.BROKEN and moves < MAX_CHECKPOINT_MOVES:
            latest: AuditChainCheckpointDocument | None = (
                self._chain_repo.checkpoint_of(chain_key)
            )
            if not moved_on(checkpoint, latest):
                break

            checkpoint = latest
            status = self._check(chain_key, checkpoint, previous, now)
            moves += 1

        return status

    def _check(
        self,
        chain_key: AuditChainKey,
        checkpoint: AuditChainCheckpointDocument | None,
        previous: AuditChainStatusDocument | None,
        now: Microseconds,
    ) -> AuditChainStatusDocument:
        """One check of the chain from `checkpoint` on."""

        start: ChainWalk = walk_from_checkpoint(checkpoint)
        finding: ChainFinding | None = self._find_lost_entries(
            chain_key, checkpoint, previous, start.position, now
        )
        walk: ChainWalk = start
        if finding is None:
            walk = self._resumed(chain_key, previous, start)
            finding = walk_chain(self._chain_repo, chain_key, walk, self._max_entries)

        return chain_status(chain_key, previous, walk, finding, now)

    def _find_lost_entries(
        self,
        chain_key: AuditChainKey,
        checkpoint: AuditChainCheckpointDocument | None,
        previous: AuditChainStatusDocument | None,
        start: AuditChainPosition,
        now: Microseconds,
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

        if previous is None or previous.verified_through_position is None:
            return None

        anchor: AuditChainPosition = previous.verified_through_position
        if checkpoint is not None and int(anchor) <= int(checkpoint.through_position):
            # A purge removed the newest entry the last check verified: only
            # a cutoff past the minimum retention explains that.
            if is_cutoff_allowed(checkpoint.purged_before, now):
                return None

            return ChainFinding(AuditChainProblem.HEAD_LOST, anchor)

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

        before: AuditChainPosition | None = position_before(previous.resume_position)
        found: list[AuditLogEntryDocument] = (
            []
            if before is None
            else self._chain_repo.entries_from(chain_key, before, ONE)
        )
        if (
            not found
            or found[0].chain_position != before
            or found[0].entry_hash is None
        ):
            return start

        return ChainWalk(
            start=previous.resume_position,
            position=previous.resume_position,
            expected_prev=found[0].entry_hash,
        )


def moved_on(
    checkpoint: AuditChainCheckpointDocument | None,
    latest: AuditChainCheckpointDocument | None,
) -> bool:
    """Whether a purge moved the chain's checkpoint past `checkpoint`."""

    if latest is None:
        return False

    return checkpoint is None or int(latest.through_position) > int(
        checkpoint.through_position
    )
