from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.access_tokens import hash_access_token

INVALID_SESSION_MESSAGE: str = "The session is invalid or has expired; sign in again."


class AuthenticateUserUseCase(UseCaseContract[AccessToken, SessionAssurance]):
    """
    Resolve a bearer token to the signed-in session: whose it is, how it
    was signed in and when its person last proved it is them.

    The token is looked up by its hash. An expired session is deleted on
    sight; unknown and expired tokens and deleted users are all reported as
    AuthenticationRequiredError. A session from before two-factor sign-in
    (no `auth_level`) counts as one factor, not recently confirmed.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        user_repo: UserRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._user_repo: UserRepoContract = user_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AccessToken) -> SessionAssurance:
        session: UserSessionDocument | None = (
            self._user_session_repo.find_by_token_hash(hash_access_token(input_data))
        )
        if session is None:
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        if self._wall_clock.now_unix() >= session.expires_at:
            self._user_session_repo.delete(session.id)
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        user: UserDocument | None = self._user_repo.get(session.user_id)
        if user is None:
            self._user_session_repo.delete(session.id)
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        return SessionAssurance(
            user_id=user.id,
            session_id=session.id,
            auth_level=session.auth_level or AuthLevel.ONE_FACTOR,
            authenticated_at=session.authenticated_at,
        )
