"""
Shared steps of the public API's reads: the key's business, and the audit
entry of what a key read (the key's id, how many records, its owner as
the actor), so the owner's Settings → Records show every read.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.public_api.access import ApiKeyPrincipal
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.shared.operations_support import build_audit_entry

API_BOOKING_ENTITY: AuditEntityName = AuditEntityName("api_booking")
API_LEAD_ENTITY: AuditEntityName = AuditEntityName("api_lead")
API_CONTACT_ENTITY: AuditEntityName = AuditEntityName("api_contact")
API_CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("api_conversation")
GONE_BUSINESS_MESSAGE: str = "The business of this API key is gone."


def key_business(
    business_repo: BusinessRepoContract, principal: ApiKeyPrincipal
) -> BusinessDocument:
    business = business_repo.get(principal.business_id)
    if business is None:
        raise AuthenticationRequiredError(GONE_BUSINESS_MESSAGE)

    return business


def record_public_read(
    audit_log_repo: AuditLogRepoContract,
    principal: ApiKeyPrincipal,
    entity: AuditEntityName,
    record_count: int,
    now: Microseconds,
) -> None:
    """An audit entry `view <entity>` of the key, with how many it read."""

    entry = build_audit_entry(
        principal.business_id,
        principal.created_by,
        AuditAction.VIEW,
        entity,
        str(principal.api_key_id),
        now,
        principal.client_ip_address,
    )
    audit_log_repo.append(
        entry.model_copy(update={"record_count": AuditRecordCount(record_count)})
    )
