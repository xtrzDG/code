from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import SessionSweepReason
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import (
    RevokeAllSessionsCommand,
    RevokedSessionsView,
    SessionSweep,
)
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.shared.session_sweeps import end_sessions


class RevokeAllSessionsUseCase(
    UseCaseContract[RevokeAllSessionsCommand, RevokedSessionsView]
):
    """
    "Sign out everywhere": end every session of the person, the request's
    own too, so every device (this one included) must sign in again; each
    ended token stops working with its next request. Audited once as
    SESSION_REVOKED with the count and the address. Needs the request's
    session (the person proves who they are with it).
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

    def run(self, input_data: RevokeAllSessionsCommand) -> RevokedSessionsView:
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.user_id != input_data.user_id:
            raise AuthenticationRequiredError("Sign in to sign out everywhere.")

        ended: DocumentCount = end_sessions(
            self._user_session_repo,
            self._audit_log_repo,
            SessionSweep(
                user_id=input_data.user_id,
                actor_id=input_data.user_id,
                reason=SessionSweepReason.SIGNED_OUT_EVERYWHERE,
                client_ip_address=input_data.client_ip_address,
                now=self._wall_clock.now_unix(),
            ),
        )
        return RevokedSessionsView(revoked_count=ended)
