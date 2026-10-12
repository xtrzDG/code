"""
Appending an entry to its hash chain: under the chain's advisory lock, in
one transaction, read the chain's newest entry (or the checkpoint a purge
left when the chain holds none), link the entry after it and insert it.

The lock orders every append of one chain across processes, so two
writers never take the same position; the unique index on (chain,
position) (migration 1193) refuses a second entry at a position even if
they did. Only audit entries are chained, and the lock is the chain's own,
so no other write waits for it.
"""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.repositories.audit.audit_chain_queries import (
    CHAIN_POSITION_FIELD,
    of_chain,
)
from app.repositories.document_queries import descending
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentQueryLimit,
    LockWaitSeconds,
)
from app.utilities.compliance.audit_chain_hashing import (
    FIRST_POSITION,
    GENESIS_HASH,
    chain_key_of,
    chain_lock_key,
    link_entry,
)

# The locked section reads one row and inserts one: well under a second.
AUDIT_CHAIN_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)
ONE: DocumentQueryLimit = DocumentQueryLimit(1)


class AuditChainAppending:
    """Links each new entry to the newest one of its chain."""

    def __init__(
        self,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
        advisory_locks: AdvisoryLockAdapterContract,
    ) -> None:
        self._entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            entries
        )
        self._checkpoints: DocumentCollectionAdapterContract[
            AuditChainCheckpointDocument
        ] = checkpoints
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def append(self, entry: AuditLogEntryDocument) -> AuditLogEntryDocument:
        """
        Store the entry at the end of its chain; returns it as stored.

        Raises:
            ConflictError: an entry with this id is stored already.
        """

        chain_key: AuditChainKey = chain_key_of(entry.business_id)
        with self._advisory_locks.hold_with_transaction(
            chain_lock_key(chain_key), AUDIT_CHAIN_LOCK_WAIT
        ):
            position, prev_hash = self._next_link(chain_key)
            linked: AuditLogEntryDocument = link_entry(entry, position, prev_hash)
            if not self._entries.insert_if_absent(str(entry.id), linked):
                raise ConflictError(
                    f"Audit entry {entry.id} is already stored, or its chain "
                    "position was taken."
                )

        return linked

    def head_of(self, chain_key: AuditChainKey) -> AuditLogEntryDocument | None:
        """The newest entry of a chain; None when it holds none."""

        newest: list[AuditLogEntryDocument] = self._entries.list_by_fields(
            (of_chain(chain_key),),
            order=descending(CHAIN_POSITION_FIELD),
            limit=ONE,
        )
        return newest[0] if newest else None

    def _next_link(
        self, chain_key: AuditChainKey
    ) -> tuple[AuditChainPosition, AuditEntryHash]:
        """The position of the next entry and the hash it links to."""

        head: AuditLogEntryDocument | None = self.head_of(chain_key)
        if head is not None:
            if head.chain_position is None or head.entry_hash is None:
                raise ConflictError(f"The audit chain {chain_key} has no linked head.")

            return AuditChainPosition(int(head.chain_position) + 1), head.entry_hash

        checkpoint: AuditChainCheckpointDocument | None = self._checkpoints.get(
            str(chain_key)
        )
        if checkpoint is None:
            return FIRST_POSITION, GENESIS_HASH

        return (
            AuditChainPosition(int(checkpoint.through_position) + 1),
            checkpoint.through_hash,
        )
