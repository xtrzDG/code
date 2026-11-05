"""The audit entry of an announcement change: it reaches every owner."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId

ANNOUNCEMENT_ENTITY: AuditEntityName = AuditEntityName("platform_announcement")


def audit_announcement(
    audit_log_repo: AuditLogRepoContract,
    announcement: PlatformAnnouncementDocument,
    action: AuditAction,
    admin_id: UserId,
    ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """A platform-wide entry (no business), like the admin team's changes."""

    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=admin_id,
            action=action,
            entity=ANNOUNCEMENT_ENTITY,
            entity_id=AuditEntityReference(str(announcement.id)),
            ip_address=ip_address,
            created_at=now,
            updated_at=now,
        )
    )
