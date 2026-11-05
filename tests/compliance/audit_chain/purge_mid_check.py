"""
A chain repository whose reads let a purge commit between them: the
operator's `workshop purge-audit-log` running while the daily check walks
the chain. Each storage read of the check is its own statement, so a purge
can commit before any of them.
"""

from collections.abc import Callable

from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.schemas.constants.compliance import AuditChainStatus
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainStatusDocument,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)


class PurgeBeforeEntryRead(AuditChainRepoContract):
    """
    The chain's repository, except that the purge `commit_purge` runs just
    before the check's `read_number`-th read of entries (counted from 1).
    """

    def __init__(
        self,
        chains: AuditChainRepoContract,
        read_number: int,
        commit_purge: Callable[[], object],
    ) -> None:
        self._chains: AuditChainRepoContract = chains
        self._read_number: int = read_number
        self._commit_purge: Callable[[], object] = commit_purge
        self.entry_reads: int = 0

    def head_of(self, chain_key: AuditChainKey) -> AuditLogEntryDocument | None:
        return self._chains.head_of(chain_key)

    def entries_from(
        self,
        chain_key: AuditChainKey,
        position: AuditChainPosition,
        limit: DocumentQueryLimit,
    ) -> list[AuditLogEntryDocument]:
        self.entry_reads += 1
        if self.entry_reads == self._read_number:
            self._commit_purge()

        return self._chains.entries_from(chain_key, position, limit)

    def checkpoint_of(
        self, chain_key: AuditChainKey
    ) -> AuditChainCheckpointDocument | None:
        return self._chains.checkpoint_of(chain_key)

    def status_of(self, chain_key: AuditChainKey) -> AuditChainStatusDocument | None:
        return self._chains.status_of(chain_key)

    def save_status(self, status: AuditChainStatusDocument) -> None:
        self._chains.save_status(status)

    def count_by_status(self) -> dict[AuditChainStatus, DocumentCount]:
        return self._chains.count_by_status()

    def list_broken(self, limit: DocumentQueryLimit) -> list[AuditChainStatusDocument]:
        return self._chains.list_broken(limit)
