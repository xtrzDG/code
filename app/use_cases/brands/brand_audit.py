"""
Brand changes in the audit logs of the locations they reach: whoever
gains or loses access to a location through its brand shows in that
location's own log, so its owners see who may open their cabinet.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

BRAND_MEMBER_ENTITY: AuditEntityName = AuditEntityName("brand_member")
BRAND_LOCATION_ENTITY: AuditEntityName = AuditEntityName("brand_location")


def record_in_locations(
    audit_log_repo: AuditLogRepoContract,
    location_ids: list[BusinessId],
    actor_id: UserId,
    action: AuditAction,
    entity: AuditEntityName,
    entity_reference: AuditEntityReference,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """One entry in the log of each location (in their order, once each)."""

    for location_id in dict.fromkeys(location_ids):
        audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=location_id,
                actor_id=actor_id,
                action=action,
                entity=entity,
                entity_id=entity_reference,
                ip_address=client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
