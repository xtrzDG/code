from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import (
    AuditChainPosition,
    AuditRecordCount,
)
from app.schemas.typings.compliance.constrained_strings import (
    AuditChainKey,
    AuditEntryHash,
    DpaDocumentVersion,
)
from app.schemas.typings.compliance.prefixed_id import (
    AuditLogEntryId,
    DpaAcceptanceId,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId


class AuditLogEntryDocument(BaseDocument):
    """
    One operation on personal data (concept table `audit_logs`).

    `actor_id` is null for automatic jobs such as retention purges.

    The log is append-only and hash-chained: every entry written since
    version 6 sits in one chain (`chain_key`: its business, or `platform`
    for the entries that name none) at `chain_position`, names the hash
    of the entry before it (`prev_hash`, 64 zeros for the first) and
    carries the SHA-256 of its own canonical JSON (`entry_hash`,
    `app/utilities/compliance/audit_chain_hashing.py`). Entries written
    before version 6 hold no chain fields; they stay as they were.
    """

    # 2: the action `mfa_changed`. Its entries are about a person, not a
    # business (no `business_id`), and every reader of the previous release
    # lists entries by business, so it never meets one.
    # 3: the actions `session_revoked` and `platform_admin_changed` (about a
    # person, no business, like `mfa_changed`) and `support_access_start`
    # and `support_access_end` (in the business's log; an exception to the
    # enum rule, docs/operations/deploys.md).
    # 4: `record_count`, how many records a purge or a deletion at a
    # sub-processor covered (optional, so version 3 needs no upcaster).
    # 5: the actions `spend_limit_reached` (R12) and ADMIN_* on a client's
    # account (R13; in the business's log, an exception to the enum rule,
    # docs/operations/deploys.md) and the admin's `reason` (optional).
    # 6: the hash chain (`chain_key`, `chain_position`, `prev_hash`,
    # `entry_hash`) and `security_event` (sign-in failures and lockouts,
    # sign-outs, key rotations), all optional: a version 5 row reads as an
    # entry from before the chain. The previous release ignores the new
    # fields, and every security event rides on an action it reads.
    schema_version: SchemaVersion = SchemaVersion("6")
    id: AuditLogEntryId = Field(default_factory=AuditLogEntryId)
    business_id: BusinessId | None = None
    actor_id: UserId | None = None
    action: AuditAction
    entity: AuditEntityName
    entity_id: AuditEntityReference | None = None
    ip_address: ClientIpAddress | None = None
    record_count: AuditRecordCount | None = None
    reason: AdminActionReason | None = None
    security_event: AuditSecurityEvent | None = None
    chain_key: AuditChainKey | None = None
    chain_position: AuditChainPosition | None = None
    prev_hash: AuditEntryHash | None = None
    entry_hash: AuditEntryHash | None = None


class DpaAcceptanceDocument(BaseDocument):
    """Acceptance of the data processing agreement (concept `dpa_acceptances`)."""

    id: DpaAcceptanceId = Field(default_factory=DpaAcceptanceId)
    business_id: BusinessId
    document_version: DpaDocumentVersion
    accepted_by: UserId
    accepted_at: Microseconds
