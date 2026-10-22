from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import UserSessionRepoContract
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.dto.mfa import SessionAssurance, SessionAssuranceView
from app.schemas.dto.passkeys import VerifyPasskeyStepUpCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.mfa.mfa_check_limits import (
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.passkeys.passkey_assertions import PasskeyAssertionCheck
from app.use_cases.users.passkeys.passkey_challenges import take_passkey_challenge
from app.use_cases.users.passkeys.start_passkey_step_up_use_case import (
    NO_SESSION_MESSAGE,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


class VerifyPasskeyStepUpUseCase(
    UseCaseContract[VerifyPasskeyStepUpCommand, SessionAssuranceView]
):
    """
    The signed-in person confirms it is them with a passkey: their session
    counts as two factors and may do sensitive actions for
    STEP_UP_MAX_AGE_SECONDS again. Checks share the per-person and
    per-network budget of authenticator codes; the challenge is taken
    once; a refused answer leaves the session as it was.
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        audit_log_repo: AuditLogRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._assertion: PasskeyAssertionCheck = PasskeyAssertionCheck(
            passkey_repo, ceremony, audit_log_repo
        )

    def run(self, input_data: VerifyPasskeyStepUpCommand) -> SessionAssuranceView:
        now: Microseconds = self._wall_clock.now_unix()
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.user_id != input_data.user_id:
            raise AuthenticationRequiredError(NO_SESSION_MESSAGE)

        refuse_too_frequent_second_factor_checks(
            self._rate_limit_registry,
            self._app_settings,
            RateLimitKey(f"mfa-check:user:{input_data.user_id}"),
            input_data.client_ip_address,
            now,
        )
        challenge: PasskeyChallengeDocument = take_passkey_challenge(
            self._challenge_repo,
            input_data.passkey_challenge_id,
            input_data.user_id,
            PasskeyCeremonyPurpose.STEP_UP,
            now,
        )
        self._assertion.verify(
            challenge, input_data.credential, input_data.client_ip_address, now
        )
        self._user_session_repo.record_authentication(
            assurance.session_id, AuthLevel.TWO_FACTOR, now
        )
        return SessionAssuranceView(
            auth_level=AuthLevel.TWO_FACTOR,
            authenticated_at=now,
            step_up_valid_until=Microseconds(
                int(now)
                + int(self._app_settings.step_up_max_age_seconds)
                * MICROSECONDS_PER_SECOND
            ),
        )
