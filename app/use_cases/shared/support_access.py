"""
Platform support's grants, shared by the admin side (opening and closing
a look into a cabinet, the expiry job), the owner side (the banner, the
consent, ending support's access) and the access check of every request.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.support_access import SupportAccessGrantRepoContract
from app.schemas.constants.access import (
    PlatformAdminPermission,
    PlatformAdminRole,
    SupportAccessKind,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.dto.support_access import SupportAccessEnding
from app.schemas.typings.compliance.prefixed_id import AuditLogEntryId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.admin_permissions import has_permission

SUPPORT_ACCESS_ENTITY: AuditEntityName = AuditEntityName("support_access")
SUPPORT_WRITE_ACCESS_ENTITY: AuditEntityName = AuditEntityName("support_write_access")
SUPPORT_SESSION_MINUTES: int = 60
DEFAULT_WRITE_ACCESS_HOURS: int = 24
MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000


def is_live(grant: SupportAccessGrantDocument, now: Microseconds) -> bool:
    """Open and not yet past its end."""

    return grant.ended_at is None and int(now) < int(grant.expires_at)


def live_sessions(
    grants: Sequence[SupportAccessGrantDocument], now: Microseconds
) -> list[SupportAccessGrantDocument]:
    return [
        grant
        for grant in grants
        if grant.kind is SupportAccessKind.SESSION and is_live(grant, now)
    ]


def live_write_consent(
    grants: Sequence[SupportAccessGrantDocument], now: Microseconds
) -> SupportAccessGrantDocument | None:
    """The owner's consent to changes that is in force, the latest one."""

    consents: list[SupportAccessGrantDocument] = [
        grant
        for grant in grants
        if grant.kind is SupportAccessKind.WRITE_CONSENT and is_live(grant, now)
    ]
    return max(consents, key=lambda grant: int(grant.expires_at), default=None)


def end_grant(
    grant_repo: SupportAccessGrantRepoContract,
    audit_log_repo: AuditLogRepoContract,
    grant: SupportAccessGrantDocument,
    ending: SupportAccessEnding,
    client_ip_address: ClientIpAddress | None,
) -> SupportAccessGrantDocument | None:
    """
    End the grant once (compare-and-swap) and audit it: SUPPORT_ACCESS_END
    for a support session, UPDATE of the write access for the owner's
    consent. None when it had already ended.
    """

    ended: SupportAccessGrantDocument | None = grant_repo.end(
        grant.business_id, grant.id, ending
    )
    if ended is None:
        return None

    is_session: bool = grant.kind is SupportAccessKind.SESSION
    audit_support_access(
        audit_log_repo,
        ended,
        AuditAction.SUPPORT_ACCESS_END if is_session else AuditAction.UPDATE,
        actor_id=ending.ended_by,
        client_ip_address=client_ip_address,
        now=ending.ended_at,
    )
    return ended


def can_support_write(
    role: PlatformAdminRole | None,
    grants: Sequence[SupportAccessGrantDocument],
    now: Microseconds,
) -> bool:
    """The admin's role may change cabinets and the owner's consent holds."""

    return (
        has_permission(role, PlatformAdminPermission.CHANGE_CLIENT_CABINET)
        and live_write_consent(grants, now) is not None
    )


def audit_support_access(
    audit_log_repo: AuditLogRepoContract,
    grant: SupportAccessGrantDocument,
    action: AuditAction,
    actor_id: UserId | None,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> AuditLogEntryId:
    """An entry in the business's audit log naming the grant; its id."""

    entry = AuditLogEntryDocument(
        business_id=grant.business_id,
        actor_id=actor_id,
        action=action,
        entity=(
            SUPPORT_ACCESS_ENTITY
            if grant.kind is SupportAccessKind.SESSION
            else SUPPORT_WRITE_ACCESS_ENTITY
        ),
        entity_id=AuditEntityReference(str(grant.id)),
        ip_address=client_ip_address,
        created_at=now,
        updated_at=now,
    )
    audit_log_repo.append(entry)
    return entry.id
