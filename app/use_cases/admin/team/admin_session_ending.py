"""The end of a changed or removed platform admin's sessions."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import SessionAssuranceContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.sessions import SessionSweep
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.team.admin_team import signed_in_user
from app.use_cases.shared.session_sweeps import end_sessions, own_session


class AdminSessionEnding:
    """
    A changed or removed admin signs in again: every session of theirs ends
    (SESSION_REVOKED with the count, by the SUPER admin who made the
    change), so no device keeps rights it was signed in with. When admins
    change their own role, the request's session stays.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def end(
        self,
        admin: PlatformAdminDocument,
        actor_id: UserId,
        client_ip_address: ClientIpAddress | None,
        now: Microseconds,
    ) -> None:
        user: UserDocument | None = signed_in_user(self._user_repo, admin)
        if user is None:
            return

        end_sessions(
            self._user_session_repo,
            self._audit_log_repo,
            SessionSweep(
                user_id=user.id,
                actor_id=actor_id,
                reason=SessionSweepReason.ADMIN_ROLE_CHANGED,
                kept_session_id=own_session(self._session_assurance, user.id),
                client_ip_address=client_ip_address,
                now=now,
            ),
        )
