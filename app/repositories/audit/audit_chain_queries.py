"""The lookup fields of the audit log's hash chains and the queries on them."""

from app.repositories.document_queries import field_equals
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFieldRange
from app.schemas.typings.compliance.constrained_integers import AuditChainPosition
from app.schemas.typings.compliance.constrained_strings import AuditChainKey
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

CHAIN_KEY_FIELD: DocumentFieldPath = DocumentFieldPath("chain_key")
CHAIN_POSITION_FIELD: DocumentFieldPath = DocumentFieldPath("chain_position")
SECURITY_EVENT_FIELD: DocumentFieldPath = DocumentFieldPath("security_event")
ENTITY_ID_FIELD: DocumentFieldPath = DocumentFieldPath("entity_id")


def of_chain(chain_key: AuditChainKey) -> DocumentFieldMatch:
    """The entries of one chain."""

    return field_equals(CHAIN_KEY_FIELD, chain_key)


def positions_from(position: AuditChainPosition) -> DocumentFieldRange:
    """Chain positions from `position` on (inclusive)."""

    return DocumentFieldRange(
        field=CHAIN_POSITION_FIELD, lower=DocumentFieldInteger(int(position))
    )
