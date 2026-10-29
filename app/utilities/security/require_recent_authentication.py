from typed_time_provider import Microseconds, WallClock

from app.contracts.session_assurance import (
    SessionAssuranceContract,
    StepUpGuardContract,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.mfa.constrained_integers import StepUpMaxAgeSeconds
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

MICROSECONDS_PER_SECOND: int = 1_000_000
STEP_UP_REQUIRED_CODE: ErrorReasonCode = ErrorReasonCode("step_up_required")
STEP_UP_MESSAGE: str = (
    "Confirm it is you to do this: enter a code from your authenticator app "
    "or the login code we send you."
)


class RequireRecentAuthentication(StepUpGuardContract):
    """
    Step-up of sensitive actions (exports and erasures of personal data,
    team changes, connecting a channel, the platform admin opening a
    client's cabinet or re-encrypting secrets): the session must have
    proved its person within `max_age` (STEP_UP_MAX_AGE_SECONDS, ten
    minutes by default): at sign-in, or since with `/v1/auth/step-up`.

    A refusal is StepUpRequiredError (HTTP 401, reason `step_up_required`
    with the window in seconds as its detail); the session stays valid.
    Without a bound session (code outside a signed-in request) it refuses
    too: no sensitive action runs in the background.
    """

    def __init__(
        self,
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
        max_age: StepUpMaxAgeSeconds,
    ) -> None:
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._max_age: StepUpMaxAgeSeconds = max_age

    def require_recent_authentication(self) -> None:
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.authenticated_at is None:
            raise self._refusal()

        age: int = int(self._wall_clock.now_unix()) - int(assurance.authenticated_at)
        if age < 0 or age > int(self._max_age) * MICROSECONDS_PER_SECOND:
            raise self._refusal()

    def _refusal(self) -> StepUpRequiredError:
        return StepUpRequiredError(
            STEP_UP_MESSAGE,
            reasons=[
                ErrorReason(
                    code=STEP_UP_REQUIRED_CODE,
                    message=ErrorReasonMessage(STEP_UP_MESSAGE),
                    details=[ErrorReasonDetail(str(int(self._max_age)))],
                )
            ],
        )
