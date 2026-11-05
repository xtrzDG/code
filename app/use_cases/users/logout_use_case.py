from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.users import LogoutCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.use_cases.users.sign_in_security_audit import signed_out_entry
from app.utilities.security.access_tokens import hash_access_token


class LogoutUseCase(UseCaseContract[LogoutCommand, None]):
    """
    End the session behind a bearer token; the sign-out is audited as
    LOGOUT in the platform's chain, with the person and the address.

    An expired session is still deleted; an unknown token is reported as
    AuthenticationRequiredError.
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

    def run(self, input_data: LogoutCommand) -> None:
        session: UserSessionDocument | None = (
            self._user_session_repo.find_by_token_hash(
                hash_access_token(input_data.access_token)
            )
        )
        if session is None:
            raise AuthenticationRequiredError("The session was not found.")

        self._user_session_repo.delete(session.id)
        self._audit_log_repo.append(
            signed_out_entry(
                session, input_data.client_ip_address, self._wall_clock.now_unix()
            )
        )
