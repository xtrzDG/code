from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.session_assurance import SessionAssuranceContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument, PasskeyDocument
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.dto.passkeys import PasskeyAssertionOptionsView, PasskeyCommand
from app.schemas.exceptions.application_errors import AuthenticationRequiredError
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.use_cases.shared.second_factors import usable_passkeys
from app.use_cases.users.passkeys.passkey_challenges import issue_passkey_challenge
from app.use_cases.users.passkeys.passkey_request_limits import (
    refuse_too_many_passkey_requests,
)
from app.use_cases.users.passkeys.start_passkey_sign_in_use_case import (
    NO_PASSKEY_MESSAGE,
)
from app.utilities.security.passkey_policy import passkeys_unavailable

NO_SESSION_MESSAGE: str = "Sign in again to confirm it is you."


class StartPasskeyStepUpUseCase(
    UseCaseContract[PasskeyCommand, PasskeyAssertionOptionsView]
):
    """
    The signed-in person confirms it is them with a passkey before a
    sensitive action: the options for `navigator.credentials.get()` with
    their passkeys, under a challenge bound to them. At most ten requests
    per person in ten minutes.
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        session_assurance: SessionAssuranceContract,
        wall_clock: WallClock[Microseconds],
        rate_limit_registry: RequestRateLimitRegistryContract,
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._session_assurance: SessionAssuranceContract = session_assurance
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )

    def run(self, input_data: PasskeyCommand) -> PasskeyAssertionOptionsView:
        assurance: SessionAssurance | None = self._session_assurance.current()
        if assurance is None or assurance.user_id != input_data.user_id:
            raise AuthenticationRequiredError(NO_SESSION_MESSAGE)

        refuse_too_many_passkey_requests(
            self._rate_limit_registry,
            RateLimitKey(f"passkey-options:user:{input_data.user_id}"),
            self._wall_clock.now_unix(),
        )
        if not self._ceremony.is_available():
            raise passkeys_unavailable()

        passkeys: list[PasskeyDocument] = usable_passkeys(
            self._passkey_repo, input_data.user_id
        )
        if not passkeys:
            raise passkeys_unavailable(NO_PASSKEY_MESSAGE)

        challenge: PasskeyChallengeDocument = issue_passkey_challenge(
            self._challenge_repo,
            self._ceremony,
            self._wall_clock,
            input_data.user_id,
            PasskeyCeremonyPurpose.STEP_UP,
        )
        return PasskeyAssertionOptionsView(
            passkey_challenge_id=challenge.id,
            options=self._ceremony.request_options(challenge.challenge, passkeys),
        )
