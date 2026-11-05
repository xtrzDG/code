"""
A change of how a person proves it is them reaches every session of theirs:
sessions are lowered to one factor (an authenticator removed, recovery codes
replaced) or ended (a new authenticator, a platform-admin role changed).
Ended sessions are audited here as SESSION_REVOKED with their count;
the count of lowered ones goes on the MFA_CHANGED entry of the change
itself. The entries are about a person and name no business.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionSweep
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId, UserSessionId

SWEPT_SESSIONS_ENTITY: AuditEntityName = AuditEntityName("user_session")


def own_session(
    session_assurance: SessionAssuranceContract, user_id: UserId
) -> UserSessionId | None:
    """The request's session when it is this person's: a sweep keeps it."""

    assurance: SessionAssurance | None = session_assurance.current()
    if assurance is None or assurance.user_id != user_id:
        return None

    return assurance.session_id


def end_sessions(
    user_session_repo: UserSessionRepoContract,
    audit_log_repo: AuditLogRepoContract,
    sweep: SessionSweep,
) -> DocumentCount:
    """
    End every session of `sweep.user_id` but the kept one; audited as
    SESSION_REVOKED with the count when any ended.
    """

    ended: DocumentCount = user_session_repo.delete_for_user(
        sweep.user_id, sweep.kept_session_id
    )
    if int(ended) == 0:
        return ended

    now: Microseconds = sweep.now
    audit_log_repo.append(
        AuditLogEntryDocument(
            actor_id=sweep.actor_id,
            action=AuditAction.SESSION_REVOKED,
            entity=SWEPT_SESSIONS_ENTITY,
            entity_id=AuditEntityReference(f"{sweep.user_id}:{sweep.reason.value}"),
            ip_address=sweep.client_ip_address,
            record_count=AuditRecordCount(int(ended)),
            created_at=now,
            updated_at=now,
        )
    )
    return ended


def lower_sessions(
    user_session_repo: UserSessionRepoContract,
    sweep: SessionSweep,
) -> DocumentCount:
    """
    Make every session of `sweep.user_id` but the kept one count as one
    factor: admin pages and team two-factor rules refuse them until the
    person confirms again with a factor they still have. Returns how many
    sessions were two-factor.
    """

    return user_session_repo.set_level_for_user(
        sweep.user_id, AuthLevel.ONE_FACTOR, sweep.now, sweep.kept_session_id
    )
