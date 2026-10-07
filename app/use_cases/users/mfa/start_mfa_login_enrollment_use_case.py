from typed_time_provider import Microseconds, WallClock

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import StartMfaEnrollmentCommand, TotpEnrollmentView
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.users.mfa.mfa_challenges import (
    EXPIRED_STEP_MESSAGE,
    open_mfa_challenge,
)
from app.use_cases.users.mfa.mfa_check_limits import (
    refuse_too_frequent_second_factor_checks,
)
from app.use_cases.users.mfa.totp_enrollment import begin_totp_enrollment


class StartMfaLoginEnrollmentUseCase(
    UseCaseContract[StartMfaEnrollmentCommand, TotpEnrollmentView]
):
    """
    A platform admin without an authenticator sets one up in the middle of
    signing in (the login code already matched): a new pending
    authenticator for the step's person, shown once. Its first code, sent
    to VerifyMfaLoginUseCase, turns it on and opens the session. A person
    whose authenticator is on cannot replace it here (ConflictError).
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._totp_secret_cipher: TotpSecretCipherAdapterContract = totp_secret_cipher
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )

    def run(self, input_data: StartMfaEnrollmentCommand) -> TotpEnrollmentView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_second_factor_checks(
            self._rate_limit_registry,
            self._app_settings,
            RateLimitKey(f"mfa-enroll:challenge:{input_data.mfa_challenge_id}"),
            input_data.client_ip_address,
            now,
        )
        challenge: MfaChallengeDocument = open_mfa_challenge(
            self._mfa_challenge_repo, input_data.mfa_challenge_id, now
        )
        user: UserDocument | None = self._user_repo.get(challenge.user_id)
        if user is None:
            raise AuthenticationRequiredError(EXPIRED_STEP_MESSAGE)

        return begin_totp_enrollment(
            self._totp_factor_repo,
            self._totp_secret_cipher,
            self._app_settings,
            user,
            now,
        )
