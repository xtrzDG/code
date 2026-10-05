from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.typings.access.constrained_strings import AdminActionReason
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.constrained_strings import DpaDocumentVersion
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
    schema_version: SchemaVersion = SchemaVersion("5")
    id: AuditLogEntryId = Field(default_factory=AuditLogEntryId)
    business_id: BusinessId | None = None
    actor_id: UserId | None = None
    action: AuditAction
    entity: AuditEntityName
    entity_id: AuditEntityReference | None = None
    ip_address: ClientIpAddress | None = None
    record_count: AuditRecordCount | None = None
    reason: AdminActionReason | None = None


class DpaAcceptanceDocument(BaseDocument):
    """Acceptance of the data processing agreement (concept `dpa_acceptances`)."""

    id: DpaAcceptanceId = Field(default_factory=DpaAcceptanceId)
    business_id: BusinessId
    document_version: DpaDocumentVersion
    accepted_by: UserId
    accepted_at: Microseconds
