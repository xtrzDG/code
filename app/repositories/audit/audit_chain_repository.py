from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.audit_chain_repositories import (
    AuditChainRepoContract,
)
from app.repositories.audit.audit_chain_queries import (
    CHAIN_POSITION_FIELD,
    of_chain,
    positions_from,
)
from app.repositories.document_queries import descending, field_equals
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
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
ONE: DocumentQueryLimit = DocumentQueryLimit(1)


class AuditChainRepository(AuditChainRepoContract):
    """
    The chains' entries by position (indexed by chain and position, 1193),
    the checkpoints purges leave and the latest check of each chain.
    Entries are only read here; the audit log repository appends them.
    """

    def __init__(
        self,
        entries: DocumentCollectionAdapterContract[AuditLogEntryDocument],
        checkpoints: DocumentCollectionAdapterContract[AuditChainCheckpointDocument],
        statuses: DocumentCollectionAdapterContract[AuditChainStatusDocument],
    ) -> None:
        self._entries: DocumentCollectionAdapterContract[AuditLogEntryDocument] = (
            entries
        )
        self._checkpoints: DocumentCollectionAdapterContract[
            AuditChainCheckpointDocument
        ] = checkpoints
        self._statuses: DocumentCollectionAdapterContract[AuditChainStatusDocument] = (
            statuses
        )

    def head_of(self, chain_key: AuditChainKey) -> AuditLogEntryDocument | None:
        newest: list[AuditLogEntryDocument] = self._entries.list_by_fields(
            (of_chain(chain_key),),
            order=descending(CHAIN_POSITION_FIELD),
            limit=ONE,
        )
        return newest[0] if newest else None

    def entries_from(
        self,
        chain_key: AuditChainKey,
        position: AuditChainPosition,
        limit: DocumentQueryLimit,
    ) -> list[AuditLogEntryDocument]:
        return self._entries.list_by_range(
            positions_from(position), (of_chain(chain_key),), limit=limit
        )

    def checkpoint_of(
        self, chain_key: AuditChainKey
    ) -> AuditChainCheckpointDocument | None:
        return self._checkpoints.get(str(chain_key))

    def status_of(self, chain_key: AuditChainKey) -> AuditChainStatusDocument | None:
        return self._statuses.get(str(chain_key))

    def save_status(self, status: AuditChainStatusDocument) -> None:
        self._statuses.upsert(str(status.id), status)

    def count_by_status(self) -> dict[AuditChainStatus, DocumentCount]:
        return {
            status: self._statuses.count_by_fields(
                (field_equals(STATUS_FIELD, status),)
            )
            for status in AuditChainStatus
        }

    def list_broken(self, limit: DocumentQueryLimit) -> list[AuditChainStatusDocument]:
        return self._statuses.list_by_fields(
            (field_equals(STATUS_FIELD, AuditChainStatus.BROKEN),), limit=limit
        )
