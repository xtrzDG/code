from app.contracts.repositories import UserSessionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserSessionDocument
from app.schemas.dto.users import LogoutCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.utilities.security.access_tokens import hash_access_token


class LogoutUseCase(UseCaseContract[LogoutCommand, None]):
    """
    End the session behind a bearer token.

    An expired session is still deleted; an unknown token is reported as
    AuthenticationRequiredError.
    """

    def __init__(self, user_session_repo: UserSessionRepoContract) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo

    def run(self, input_data: LogoutCommand) -> None:
        session: UserSessionDocument | None = (
            self._user_session_repo.find_by_token_hash(
                hash_access_token(input_data.access_token)
            )
        )
        if session is None:
            raise AuthenticationRequiredError("The session was not found.")

        self._user_session_repo.delete(session.id)
