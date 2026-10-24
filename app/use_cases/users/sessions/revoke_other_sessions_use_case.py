from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import RevokedSessionsView, RevokeOtherSessionsCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.users.sessions.session_views import audit_sessions_ended

OTHER_SESSIONS_REFERENCE: AuditEntityReference = AuditEntityReference("others")


class RevokeOtherSessionsUseCase(
    UseCaseContract[RevokeOtherSessionsCommand, RevokedSessionsView]
):
    """
    "Sign out everywhere else": end every session of the person except the
    request's own; each ended token stops working with its next request.
    Audited once as SESSION_REVOKED (when anything ended), with the address.
    Needs the request's session (it is the one kept).
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RevokeOtherSessionsCommand) -> RevokedSessionsView:
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.user_id != input_data.user_id:
            raise AuthenticationRequiredError("Sign in to end your other sessions.")

        revoked: int = 0
        for session in self._user_session_repo.list_by_user(input_data.user_id):
            if session.id == assurance.session_id:
                continue

            self._user_session_repo.delete(session.id)
            revoked += 1

        if revoked:
            audit_sessions_ended(
                self._audit_log_repo,
                input_data.user_id,
                OTHER_SESSIONS_REFERENCE,
                input_data.client_ip_address,
                self._wall_clock.now_unix(),
            )

        return RevokedSessionsView(revoked_count=DocumentCount(revoked))
