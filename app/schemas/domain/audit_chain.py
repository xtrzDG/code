"""
The documents around the audit log's hash chains: counts of repeated
views, the checkpoints purges leave behind, and what the latest check of
each chain found.
"""

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditChainProblem, AuditChainStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainEntryCount,
    AuditChainPosition,
    AuditViewCount,
)
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
)
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId


class AuditViewCountDocument(BaseDocument):
    """
    How many identical views one audited VIEW stands for (collection
    `audit_view_counts`, stored under the entry's id). A VIEW identical to
    one written in the last 5 minutes (same business, person, entity,
    record and address) raises this count instead of adding an entry: the
    chained entry itself never changes. No document means one view.
    """

    id: AuditLogEntryId
    business_id: BusinessId
    view_count: AuditViewCount
    last_viewed_at: Microseconds


class AuditChainCheckpointDocument(BaseDocument):
    """
    Where a purge cut a chain (collection `audit_chain_checkpoints`, one
    per chain, under its key): every entry up to `through_position` is
    gone, and `through_hash` is the hash of the last of them, so the first
    entry left still links to it. Written only by the database's purge
    function (`workshop.purge_audit_chain`, migration 1193).
    """

    id: AuditChainKey
    business_id: BusinessId | None = None
    through_position: AuditChainPosition
    through_hash: AuditEntryHash
    purged_count: AuditChainEntryCount


class AuditChainStatusDocument(BaseDocument):
    """
    What the latest check of one chain found (collection
    `audit_chain_statuses`, under the chain's key), for the cabinet's Audit
    tab, the admin audit view and the AUDIT_CHAIN_BROKEN alert.

    `verified_through_position` and `verified_through_hash` are the newest
    entry a check verified: the next check expects to find it unchanged
    (or purged), so cutting off the end of a chain shows too. A chain
    longer than one check reads continues at `resume_position` the next
    day. A broken chain names the problem and the first entry that fails.
    """

    id: AuditChainKey
    business_id: BusinessId | None = None
    status: AuditChainStatus
    problem: AuditChainProblem | None = None
    broken_position: AuditChainPosition | None = None
    verified_through_position: AuditChainPosition | None = None
    verified_through_hash: AuditEntryHash | None = None
    resume_position: AuditChainPosition | None = None
    entries_checked: AuditChainEntryCount
    checked_at: Microseconds
