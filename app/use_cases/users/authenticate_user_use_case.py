from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import PlatformAdminRegistryContract
from app.contracts.repositories.user_repositories import (
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.sessions import SessionActivity, SessionCheck
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.utilities.security.access_tokens import hash_access_token
from app.utilities.security.session_expiry import (
    is_session_over,
    is_use_recent,
    next_activity,
)
from app.utilities.security.user_agents import names_a_device

INVALID_SESSION_MESSAGE: str = "The session is invalid or has expired; sign in again."


class AuthenticateUserUseCase(UseCaseContract[SessionCheck, SessionAssurance]):
    """
    Resolve a bearer token to the signed-in session: whose it is, how it
    was signed in and when its person last proved it is them, with the
    request's address and whether it reads or changes.

    The token is looked up by its hash. A session past its absolute end or
    unused until its idle expiry is deleted on sight; unknown and ended
    tokens and deleted users are all reported as AuthenticationRequiredError.
    A use is recorded at most every five minutes (`session_expiry.py`):
    the last-seen time and address, the browser, and the idle expiry slid
    forward (a week, or twelve hours for platform admins, whose sessions
    also end a day after sign-in). A session from before two-factor
    sign-in (no `auth_level`) counts as one factor, not recently confirmed.
    """

    def __init__(
        self,
        user_session_repo: UserSessionRepoContract,
        user_repo: UserRepoContract,
        wall_clock: WallClock[Microseconds],
        platform_admins: PlatformAdminRegistryContract,
        app_settings: AppSettings,
    ) -> None:
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._user_repo: UserRepoContract = user_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._platform_admins: PlatformAdminRegistryContract = platform_admins
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: SessionCheck) -> SessionAssurance:
        session: UserSessionDocument | None = (
            self._user_session_repo.find_by_token_hash(
                hash_access_token(input_data.access_token)
            )
        )
        if session is None:
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        now: Microseconds = self._wall_clock.now_unix()
        if is_session_over(session, now):
            self._user_session_repo.delete(session.id)
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        user: UserDocument | None = self._user_repo.get(session.user_id)
        if user is None:
            self._user_session_repo.delete(session.id)
            raise AuthenticationRequiredError(INVALID_SESSION_MESSAGE)

        self._record_use(session, user, input_data, now)
        return SessionAssurance(
            user_id=user.id,
            session_id=session.id,
            auth_level=session.auth_level or AuthLevel.ONE_FACTOR,
            authenticated_at=session.authenticated_at,
            client_ip_address=input_data.client_ip_address,
            access_mode=input_data.access_mode,
        )

    def _record_use(
        self,
        session: UserSessionDocument,
        user: UserDocument,
        check: SessionCheck,
        now: Microseconds,
    ) -> None:
        if is_use_recent(session, now):
            # The common case reads nothing more: no admin lookup either.
            return

        activity: SessionActivity = next_activity(
            session,
            self._app_settings,
            is_admin=self._platform_admins.role_of(user) is not None,
            now=now,
            client_ip_address=check.client_ip_address,
            user_agent=check.user_agent if names_a_device(check.user_agent) else None,
        )
        self._user_session_repo.record_activity(session.id, activity)
