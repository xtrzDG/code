"""
Appending an entry to its hash chain: under the chain's advisory lock, in
one transaction, read where the chain ends, link the entry after it,
insert it and move the chain's head (`audit_chain_heads`) to it.

Where a chain ends is its head document: one row read by its key, however
long the chain grows (the hot path never searches the chain). A chain
without one (no append yet, or entries from before the heads) ends at its
newest entry, else at the checkpoint a purge left, else nowhere. Should
the position after the head be taken (only a head changed outside
appends), the entry links after the chain's newest entry instead.

The lock orders every append of one chain across processes, so two
writers never take the same position; the unique index on (chain,
position) (migration 1193) refuses a second entry at a position even if
they did. Only audit entries are chained, and the lock is the chain's own,
so no other write waits for it.
"""

from dataclasses import dataclass

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.repositories.audit.audit_chain_queries import (
    CHAIN_POSITION_FIELD,
    of_chain,
)
from app.repositories.document_queries import descending
from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
)
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
    GENESIS_HASH,
    chain_key_of,
    chain_lock_key,
    link_entry_and_hash,
    position_after,
)

# The locked section reads one row and writes two: well under a second.
AUDIT_CHAIN_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)
ONE: DocumentQueryLimit = DocumentQueryLimit(1)


@dataclass(frozen=True)
class StoredLink:
    """An entry as inserted, where it stands and its hash."""

    entry: AuditLogEntryDocument
    position: AuditChainPosition
    entry_hash: AuditEntryHash


class AuditChainAppending:
    """Links each new entry to the newest one of its chain."""

    def __init__(
        self,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
        heads: DocumentCollectionAdapterContract[AuditChainHeadDocument],
        advisory_locks: AdvisoryLockAdapterContract,
    ) -> None:
        self._entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            entries
        )
        self._checkpoints: DocumentCollectionAdapterContract[
            AuditChainCheckpointDocument
        ] = checkpoints
        self._heads: DocumentCollectionAdapterContract[AuditChainHeadDocument] = heads
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
            head: AuditChainHeadDocument | None = self._heads.get(str(chain_key))
            stored = self._insert_after(
                entry,
                self._next_link(chain_key)
                if head is None
                else (head.head_position, head.head_hash),
            )
            if stored is None and head is not None:
                stored = self._insert_after(entry, self._next_link(chain_key))
            if stored is None:
                raise ConflictError(
                    f"Audit entry {entry.id} is already stored, or its chain "
                    "position was taken."
                )

            self._move_head(chain_key, stored, head)

        return stored.entry

    def head_of(self, chain_key: AuditChainKey) -> AuditLogEntryDocument | None:
        """The newest entry of a chain; None when it holds none."""

        newest: list[AuditLogEntryDocument] = self._entries.list_by_fields(
            (of_chain(chain_key),),
            order=descending(CHAIN_POSITION_FIELD),
            limit=ONE,
        )
        return newest[0] if newest else None

    def _insert_after(
        self,
        entry: AuditLogEntryDocument,
        end: tuple[AuditChainPosition | None, AuditEntryHash],
    ) -> StoredLink | None:
        """
        Insert the entry linked after `end` (a chain's last position, None
        for an empty chain, and its hash); None when its id or position is
        taken.
        """

        last_position, prev_hash = end
        position: AuditChainPosition = position_after(last_position)
        linked, entry_hash = link_entry_and_hash(entry, position, prev_hash)
        if not self._entries.insert_if_absent(str(entry.id), linked):
            return None

        return StoredLink(entry=linked, position=position, entry_hash=entry_hash)

    def _move_head(
        self,
        chain_key: AuditChainKey,
        stored: StoredLink,
        head: AuditChainHeadDocument | None,
    ) -> None:
        """The chain's head is the entry just inserted."""

        written_at = stored.entry.created_at
        self._heads.upsert(
            str(chain_key),
            AuditChainHeadDocument(
                id=chain_key,
                business_id=stored.entry.business_id,
                head_position=stored.position,
                head_hash=stored.entry_hash,
                created_at=written_at if head is None else head.created_at,
                updated_at=written_at,
            ),
        )

    def _next_link(
        self, chain_key: AuditChainKey
    ) -> tuple[AuditChainPosition | None, AuditEntryHash]:
        """
        Where a chain without a head ends: its newest entry, else the
        checkpoint a purge left, else nowhere (None, the genesis hash).
        """

        newest: AuditLogEntryDocument | None = self.head_of(chain_key)
        if newest is not None:
            if newest.chain_position is None or newest.entry_hash is None:
                raise ConflictError(f"The audit chain {chain_key} has no linked head.")

            return newest.chain_position, newest.entry_hash

        checkpoint: AuditChainCheckpointDocument | None = self._checkpoints.get(
            str(chain_key)
        )
        if checkpoint is None:
            return None, GENESIS_HASH

        return checkpoint.through_position, checkpoint.through_hash
