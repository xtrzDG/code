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
from app.utilities.security.session_rotation_tickets import (
    grace_end,
    hash_rotation_ticket,
)

MICROSECONDS_PER_SECOND: int = 1_000_000
NO_SESSION_MESSAGE: str = "Sign in again."
NO_TICKET_MESSAGE: str = (
    "This session cannot get a new token: confirm it is you again first."
)


class RotateSessionUseCase(UseCaseContract[RotateSessionCommand, LoginSessionView]):
    """
    A fresh token for the request's session right after a proof raised it
    to two factors (POST /v1/auth/session/rotate with the one-time
    rotation ticket that proof answered: a step-up, a new authenticator or
    a first passkey; session_proofs.py). The ticket is taken once, within
    ROTATION_TICKET_TTL_SECONDS, and only with the token of the session it
    was issued to; in the same atomic step the old session winds down:
    one factor, no proof, over after ROTATION_GRACE_SECONDS (the requests
    already on their way), and it never takes a proof or a ticket again.
    A new session with a new random token carries the rest (device,
    expiries, creation) and the two factors with the ticket's proof, so a
    token copied before or after the proof never gains them. The token is
    returned once, as at sign-in.

    Without a matching ticket (none, a used or expired one, another
    session's, or a proof older than STEP_UP_MAX_AGE_SECONDS) the session
    keeps its token and is refused (409).
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

        if not self._is_recent(current.rotation_proven_at, now):
            raise ConflictError(NO_TICKET_MESSAGE)

        before: UserSessionDocument | None = (
            self._user_session_repo.take_rotation_ticket(
                current.id,
                hash_rotation_ticket(input_data.rotation_ticket),
                now,
                grace_end(now),
            )
        )
        if before is None or before.rotation_proven_at is None:
            raise ConflictError(NO_TICKET_MESSAGE)

        access_token: AccessToken = generate_access_token()
        rotated: UserSessionDocument = before.model_copy(
            update={
                "id": UserSessionId(),
                "token_hash": hash_access_token(access_token),
                "auth_level": AuthLevel.TWO_FACTOR,
                "authenticated_at": before.rotation_proven_at,
                "rotation_ticket_hash": None,
                "rotation_ticket_expires_at": None,
                "rotation_proven_at": None,
                "rotated_at": None,
                "updated_at": now,
            }
        )
        self._user_session_repo.save(rotated)
        return LoginSessionView(
            access_token=access_token,
            expires_at=rotated.expires_at,
            user=self._user_view_transformer.transform(user),
            is_new_user=IsNewUser(False),
            auth_level=AuthLevel.TWO_FACTOR,
        )

    def _is_recent(self, proven_at: Microseconds | None, now: Microseconds) -> bool:
        if proven_at is None:
            return False

        max_age: int = (
            int(self._app_settings.step_up_max_age_seconds) * MICROSECONDS_PER_SECOND
        )
        return 0 <= int(now) - int(proven_at) <= max_age
