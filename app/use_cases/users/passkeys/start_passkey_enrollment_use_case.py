from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.mfa_repositories import (
    MfaChallengeRepoContract,
    TotpFactorRepoContract,
)
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.dto.passkeys import PasskeyRegistrationView, PasskeySignInStepCommand
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.shared.second_factors import has_second_factor
from app.use_cases.users.mfa.mfa_challenges import open_mfa_step
from app.use_cases.users.passkeys.passkey_challenges import issue_passkey_challenge
from app.use_cases.users.passkeys.passkey_records import account_name_of
from app.use_cases.users.passkeys.passkey_request_limits import (
    refuse_too_many_passkey_requests,
)
from app.utilities.security.passkey_policy import passkeys_unavailable

HAS_FACTOR_MESSAGE: str = (
    "A second factor is already set up: sign in with it, then add passkeys "
    "in Account → Security."
)


class StartPasskeyEnrollmentUseCase(
    UseCaseContract[PasskeySignInStepCommand, PasskeyRegistrationView]
):
    """
    A platform admin without a second factor adds a passkey in the middle
    of signing in (the login code already matched): the options of a new
    passkey for the step's person, under a challenge bound to this step.
    The passkey is the recommended choice (phishing resistant); the
    authenticator app stays the alternative. A person who already has a
    second factor cannot add one here (ConflictError).
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )

    def run(self, input_data: PasskeySignInStepCommand) -> PasskeyRegistrationView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_many_passkey_requests(
            self._rate_limit_registry,
            RateLimitKey(f"passkey-options:challenge:{input_data.mfa_challenge_id}"),
            now,
        )
        step, user = open_mfa_step(
            self._mfa_challenge_repo, self._user_repo, input_data.mfa_challenge_id, now
        )

        if not self._ceremony.is_available():
            raise passkeys_unavailable()

        if has_second_factor(self._totp_factor_repo, self._passkey_repo, user.id):
            raise ConflictError(HAS_FACTOR_MESSAGE)

        challenge: PasskeyChallengeDocument = issue_passkey_challenge(
            self._challenge_repo,
            self._ceremony,
            self._wall_clock,
            user.id,
            PasskeyCeremonyPurpose.SIGN_IN_ENROLLMENT,
            step.id,
        )
        return PasskeyRegistrationView(
            passkey_challenge_id=challenge.id,
            options=self._ceremony.creation_options(
                user.id, account_name_of(user), challenge.challenge, []
            ),
        )
