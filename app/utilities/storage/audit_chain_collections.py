"""
The catalog entries around the audit log's hash chains (1193): the counts
of repeated views (a tenant collection), the checkpoints purges leave, the
newest entry and the latest check of each chain (platform collections: the
platform's own chain names no business). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py). The lookup fields of the audit log itself
are part of DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditChainStatusDocument,
    AuditViewCountDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import (
    filter_field,
    integer_field,
    text_field,
)

AUDIT_CHAIN_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("audit_view_counts"), AuditViewCountDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("audit_chain_checkpoints"),
        AuditChainCheckpointDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("audit_chain_heads"), AuditChainHeadDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("audit_chain_statuses"), AuditChainStatusDocument
    ),
)

# The audit log newest first, filtered by operation, entity and person; each
# hash chain by position (its head, the checks, the admin view of the
# platform's chain) and the hour's operations of every business by kind, for
# the anomaly alerts (1193).
AUDIT_LOG_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    DocumentCollectionName("audit_log_entries"): (
        text_field("actor_id"),
        text_field("action"),
        filter_field("entity"),
        integer_field("created_at"),
        text_field("chain_key"),
        integer_field("chain_position"),
        filter_field("security_event"),
        filter_field("entity_id"),
    ),
}
