"""
The catalog entries around the audit log's hash chains (1193): the counts
of repeated views (a tenant collection), the checkpoints purges leave, the
newest entry and the latest check of each chain (platform collections: the
platform's own chain names no business). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.audit_chain import (
    AuditChainCheckpointDocument,
    AuditChainHeadDocument,
    AuditChainStatusDocument,
    AuditViewCountDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
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
