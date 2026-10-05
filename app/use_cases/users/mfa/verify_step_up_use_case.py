from typed_time_provider import Microseconds, WallClock

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.mfa_repositories import (
    RecoveryCodeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import (
    OtpChallengeRepoContract,
    UserRepoContract,
    UserSessionRepoContract,
)
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.mfa import AuthLevel, TotpFactorStatus
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.users import OtpChallengeDocument, UserDocument
from app.schemas.dto.mfa import (
    SessionAssurance,
    SessionAssuranceView,
    VerifyStepUpCommand,
)
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ValidationFailedError,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.mfa.mfa_check_limits import (
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.mfa.second_factor_check import SecondFactorCheck
from app.use_cases.users.otp_login.login_challenge_consumption import (
    INVALID_CODE_MESSAGE,
    consume_login_challenge,
)
from app.utilities.security.two_factor_policy import wrong_code

MICROSECONDS_PER_SECOND: int = 1_000_000
NO_SESSION_MESSAGE: str = "Sign in again to confirm it is you."
LOGIN_CODE_NEEDED_MESSAGE: str = "Enter the login code we sent you."


class VerifyStepUpUseCase(UseCaseContract[VerifyStepUpCommand, SessionAssuranceView]):
    """
    The signed-in person confirms it is them (step-up), and their session
    may do sensitive actions for STEP_UP_MAX_AGE_SECONDS again.

    With an authenticator: its code or a recovery code (SecondFactorCheck),
    and the session counts as two factors from now on. Without one: the
    login code StartStepUpUseCase sent to their own phone or e-mail (a code
    sent to anyone else's is refused). Checks are limited per person and
    per client network; the session stays valid whatever the outcome.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        recovery_code_repo: RecoveryCodeRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
        otp_challenge_repo: OtpChallengeRepoContract,
        user_session_repo: UserSessionRepoContract,
        session_assurance: SessionAssuranceContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._otp_challenge_repo: OtpChallengeRepoContract = otp_challenge_repo
        self._user_session_repo: UserSessionRepoContract = user_session_repo
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._check: SecondFactorCheck = SecondFactorCheck(
            totp_factor_repo, recovery_code_repo, totp_secret_cipher
        )

    def run(self, input_data: VerifyStepUpCommand) -> SessionAssuranceView:
        now: Microseconds = self._wall_clock.now_unix()
        assurance: SessionAssurance | None = self._session_assurance.current()
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if assurance is None or assurance.user_id != input_data.user_id or user is None:
            raise AuthenticationRequiredError(NO_SESSION_MESSAGE)

        refuse_too_frequent_second_factor_checks(
            self._rate_limit_registry,
            self._app_settings,
            RateLimitKey(f"mfa-check:user:{user.id}"),
            input_data.client_ip_address,
            now,
        )
        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user.id)
        # Two factors only with an authenticator that is on: a login code
        # alone never keeps a level the person can no longer prove.
        auth_level: AuthLevel = AuthLevel.ONE_FACTOR
        if factor is not None and factor.status is TotpFactorStatus.ACTIVE:
            self._check.verify(user.id, input_data.code, input_data.recovery_code, now)
            auth_level = AuthLevel.TWO_FACTOR
        else:
            self._check_login_code(user, input_data, now)

        self._user_session_repo.record_authentication(
            assurance.session_id, auth_level, now
        )
        return SessionAssuranceView(
            auth_level=auth_level,
            authenticated_at=now,
            step_up_valid_until=Microseconds(
                int(now)
                + int(self._app_settings.step_up_max_age_seconds)
                * MICROSECONDS_PER_SECOND
            ),
        )

    def _check_login_code(
        self, user: UserDocument, input_data: VerifyStepUpCommand, now: Microseconds
    ) -> None:
        if input_data.challenge_id is None or input_data.login_code is None:
            raise ValidationFailedError(LOGIN_CODE_NEEDED_MESSAGE)

        try:
            challenge: OtpChallengeDocument = consume_login_challenge(
                self._otp_challenge_repo,
                self._app_settings,
                input_data.challenge_id,
                input_data.login_code,
                now,
            )
        except AuthenticationRequiredError as error:
            # A wrong code must not read as an ended session (401).
            raise wrong_code(INVALID_CODE_MESSAGE) from error

        is_own_destination: bool = (
            challenge.phone_number is not None
            and challenge.phone_number == user.phone_number
        ) or (challenge.email is not None and challenge.email == user.email)
        if not is_own_destination:
            raise wrong_code(INVALID_CODE_MESSAGE)
