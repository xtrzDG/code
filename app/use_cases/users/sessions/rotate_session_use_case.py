from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import RotateSessionCommand
from app.schemas.dto.users import LoginSessionView, UserView
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ConflictError,
)
from app.schemas.typings.users.booleans import IsNewUser
from app.schemas.typings.users.prefixed_id import UserSessionId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.access_tokens import (
    generate_access_token,
    hash_access_token,
)
from app.utilities.security.session_expiry import is_session_over

MICROSECONDS_PER_SECOND: int = 1_000_000
# How long the old token still answers the requests already on their way
# with it, as a one-factor session that can confirm nothing; without this
# such a request would be refused and the cabinet would drop the new cookie.
ROTATION_GRACE_SECONDS: int = 30
NO_SESSION_MESSAGE: str = "Sign in again."
NOT_RECENT_MESSAGE: str = "Confirm it is you first; then the session gets a new token."


class RotateSessionUseCase(UseCaseContract[RotateSessionCommand, LoginSessionView]):
    """
    A fresh token for the request's session right after a step-up (POST
    /v1/auth/session/rotate, called by the cabinet's server when a step-up
    raised the session to two factors): a new session with a new random
    token takes over everything of the old one (level, last proof, device,
    expiries, creation), so a token copied before the step-up never gains
    its level. The old session ends: for ROTATION_GRACE_SECONDS it still
    answers the requests already on their way, as one factor without a
    recent proof (what it was before the step-up), then it expires. The
    token is returned once, as at sign-in.

    Only a session whose person proved it is them within
    STEP_UP_MAX_AGE_SECONDS rotates; another is refused (409) and keeps
    its token.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RotateSessionCommand) -> LoginSessionView:
        now: Microseconds = self._wall_clock.now_unix()
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.user_id != input_data.user_id:
            raise AuthenticationRequiredError(NO_SESSION_MESSAGE)

        current: UserSessionDocument | None = self._user_session_repo.get(
            assurance.session_id
        )
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if (
            current is None
            or current.user_id != input_data.user_id
            or is_session_over(current, now)
            or user is None
        ):
            raise AuthenticationRequiredError(NO_SESSION_MESSAGE)

        if not self._is_recently_proven(current, now):
            raise ConflictError(NOT_RECENT_MESSAGE)

        access_token: AccessToken = generate_access_token()
        rotated = current.model_copy(
            update={
                "id": UserSessionId(),
                "token_hash": hash_access_token(access_token),
                "updated_at": now,
            }
        )
        self._user_session_repo.save(rotated)
        self._user_session_repo.save(winding_down(current, now))
        return LoginSessionView(
            access_token=access_token,
            expires_at=rotated.expires_at,
            user=self._user_view_transformer.transform(user),
            is_new_user=IsNewUser(False),
            auth_level=rotated.auth_level or AuthLevel.ONE_FACTOR,
        )

    def _is_recently_proven(
        self, session: UserSessionDocument, now: Microseconds
    ) -> bool:
        if session.authenticated_at is None:
            return False

        max_age: int = (
            int(self._app_settings.step_up_max_age_seconds) * MICROSECONDS_PER_SECOND
        )
        return 0 <= int(now) - int(session.authenticated_at) <= max_age


def winding_down(
    session: UserSessionDocument, now: Microseconds
) -> UserSessionDocument:
    """The old session for its last seconds: one factor, no proof, then over."""

    ends_at = Microseconds(int(now) + ROTATION_GRACE_SECONDS * MICROSECONDS_PER_SECOND)
    return session.model_copy(
        update={
            "auth_level": AuthLevel.ONE_FACTOR,
            "authenticated_at": None,
            "expires_at": min(session.expires_at, ends_at),
            "idle_expires_at": ends_at
            if session.idle_expires_at is None
            else min(session.idle_expires_at, ends_at),
            "updated_at": now,
        }
    )
