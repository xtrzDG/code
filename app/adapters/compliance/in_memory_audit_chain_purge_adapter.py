from typed_time_provider import Microseconds, WallClock

from app.contracts.audit_chain_purges import AuditChainPurgeAdapterContract
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.domain.audit_chain import AuditChainCheckpointDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditPurgeBatchSize,
)
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.utilities.compliance.audit_chain_hashing import business_of_chain


class InMemoryAuditChainPurgeAdapter(AuditChainPurgeAdapterContract):
    """
    The database function's rules over the in-memory collections (tests and
    development without a database): the same prefix, the same checkpoint.
    """

    def __init__(
        self,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            entries
        )
        self._checkpoints: DocumentCollectionAdapterContract[
            AuditChainCheckpointDocument
        ] = checkpoints
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def purge(
        self,
        chain_key: AuditChainKey,
        created_before: Microseconds,
        max_entries: AuditPurgeBatchSize,
    ) -> AuditChainEntryCount:
        business_id = business_of_chain(chain_key)
        stored: list[AuditLogEntryDocument] = [
            entry
            for entry in self._entries.list_all()
            if entry.business_id == business_id
        ]
        chained = sorted(
            (entry for entry in stored if entry.chain_key == chain_key),
            key=lambda entry: int(entry.chain_position or 0),
        )
        prefix: list[AuditLogEntryDocument] = []
        for entry in chained:
            if int(entry.created_at) >= int(created_before):
                break
            prefix.append(entry)
        batch = prefix[: int(max_entries)]
        unchained = [
            entry
            for entry in stored
            if entry.chain_key is None and int(entry.created_at) < int(created_before)
        ][: int(max_entries)]
        for entry in [*batch, *unchained]:
            self._entries.delete(str(entry.id))

        if batch:
            self._checkpoint(
                chain_key, batch[-1], len(batch), self._wall_clock.now_unix()
            )

        return AuditChainEntryCount(len(batch) + len(unchained))

    def _checkpoint(
        self,
        chain_key: AuditChainKey,
        last: AuditLogEntryDocument,
        removed: int,
        now: Microseconds,
    ) -> None:
        previous = self._checkpoints.get(str(chain_key))
        if last.chain_position is None or last.entry_hash is None:
            return

        self._checkpoints.upsert(
            str(chain_key),
            AuditChainCheckpointDocument(
                id=chain_key,
                business_id=business_of_chain(chain_key),
                through_position=last.chain_position,
                through_hash=last.entry_hash,
                purged_count=AuditChainEntryCount(
                    removed + (0 if previous is None else int(previous.purged_count))
                ),
                created_at=now if previous is None else previous.created_at,
                updated_at=now,
            ),
        )
