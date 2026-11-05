from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.mfa_repositories import MfaChallengeRepoContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.mfa import MfaChallengeDocument
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.passkeys import (
    PasskeyAssertionOptionsView,
    PasskeySignInStepCommand,
)
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.shared.second_factors import usable_passkeys
from app.use_cases.users.mfa.mfa_challenges import open_mfa_challenge
from app.use_cases.users.passkeys.passkey_challenges import issue_passkey_challenge
from app.use_cases.users.passkeys.passkey_request_limits import (
    refuse_too_many_passkey_requests,
)
from app.utilities.security.passkey_policy import passkeys_unavailable

NO_PASSKEY_MESSAGE: str = "There is no passkey to sign in with. Use another way."


class StartPasskeySignInUseCase(
    UseCaseContract[PasskeySignInStepCommand, PasskeyAssertionOptionsView]
):
    """
    The second step of a sign-in asks to use a passkey: the options for
    `navigator.credentials.get()` with the step's person's passkeys (those
    not suspected of a copy), under a challenge bound to this step. At
    most ten requests per step in ten minutes.
    """

    def __init__(
        self,
        mfa_challenge_repo: MfaChallengeRepoContract,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._mfa_challenge_repo: MfaChallengeRepoContract = mfa_challenge_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )

    def run(self, input_data: PasskeySignInStepCommand) -> PasskeyAssertionOptionsView:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_many_passkey_requests(
            self._rate_limit_registry,
            RateLimitKey(f"passkey-options:challenge:{input_data.mfa_challenge_id}"),
            now,
        )
        step: MfaChallengeDocument = open_mfa_challenge(
            self._mfa_challenge_repo, input_data.mfa_challenge_id, now
        )
        if not self._ceremony.is_available():
            raise passkeys_unavailable()

        passkeys: list[PasskeyDocument] = usable_passkeys(
            self._passkey_repo, step.user_id
        )
        if not passkeys:
            raise passkeys_unavailable(NO_PASSKEY_MESSAGE)

        challenge: PasskeyChallengeDocument = issue_passkey_challenge(
            self._challenge_repo,
            self._ceremony,
            self._wall_clock,
            step.user_id,
            PasskeyCeremonyPurpose.SIGN_IN,
            step.id,
        )
        return PasskeyAssertionOptionsView(
            passkey_challenge_id=challenge.id,
            options=self._ceremony.request_options(challenge.challenge, passkeys),
        )
