"""A session as its person sees it, and the audit entry of ending sessions."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import UserSessionView
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.schemas.typings.users.booleans import IsCurrentSession
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import describe_device

USER_SESSION_ENTITY: AuditEntityName = AuditEntityName("user_session")


def session_view(
    session: UserSessionDocument, is_current: IsCurrentSession
) -> UserSessionView:
    """A session from before devices were recorded shows its sign-in time."""

    return UserSessionView(
        id=session.id,
        device=describe_device(session.user_agent),
        auth_level=session.auth_level or AuthLevel.ONE_FACTOR,
        created_at=session.created_at,
        created_ip=session.created_ip,
        last_seen_at=session.last_seen_at or session.created_at,
        last_seen_ip=session.last_seen_ip,
        expires_at=session.expires_at,
        idle_expires_at=session.idle_expires_at,
        is_current=is_current,
    )


def audit_sessions_ended(
    audit_log_repo: AuditLogRepoContract,
    user_id: UserId,
    reference: AuditEntityReference,
    client_ip_address: ClientIpAddress | None,
    now: Microseconds,
) -> None:
    """SESSION_REVOKED by the person themselves; it names no business."""

    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=user_id,
            action=AuditAction.SESSION_REVOKED,
            entity=USER_SESSION_ENTITY,
            entity_id=reference,
            ip_address=client_ip_address,
            created_at=now,
            updated_at=now,
        )
    )
