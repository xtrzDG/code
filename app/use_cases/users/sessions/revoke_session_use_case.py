from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.sessions import RevokeSessionCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityReference
from app.use_cases.users.sessions.session_views import audit_sessions_ended


class RevokeSessionUseCase(UseCaseContract[RevokeSessionCommand, None]):
    """
    End one session of the signed-in person (a lost or shared device): its
    token stops working with its next request. Ending the request's own
    session signs this device out. Someone else's session is reported as
    missing. Audited as SESSION_REVOKED with the address.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RevokeSessionCommand) -> None:
        session: UserSessionDocument | None = self._user_session_repo.get(
            input_data.session_id
        )
        if session is None or session.user_id != input_data.user_id:
            raise NotFoundError(f"Session {input_data.session_id} was not found.")

        self._user_session_repo.delete(session.id)
        audit_sessions_ended(
            self._audit_log_repo,
            input_data.user_id,
            AuditEntityReference(str(session.id)),
            input_data.client_ip_address,
            self._wall_clock.now_unix(),
        )
