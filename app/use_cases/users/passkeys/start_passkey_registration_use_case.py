from typed_time_provider import Microseconds, WallClock

from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.passkey_repositories import (
    PasskeyChallengeRepoContract,
    PasskeyRepoContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.passkeys import PasskeyCeremonyPurpose
from app.schemas.domain.passkeys import PasskeyChallengeDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.passkeys import PasskeyCommand, PasskeyRegistrationView
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.users.passkeys.passkey_challenges import issue_passkey_challenge
from app.use_cases.users.passkeys.passkey_records import account_name_of
from app.use_cases.users.passkeys.passkey_registration import refuse_more_passkeys
from app.utilities.security.passkey_policy import passkeys_unavailable


class StartPasskeyRegistrationUseCase(
    UseCaseContract[PasskeyCommand, PasskeyRegistrationView]
):
    """
    The signed-in person starts adding a passkey, after confirming it is
    them (step-up: a stolen session must not plant its own passkey): the
    options for `navigator.credentials.create()`, with their passkeys
    excluded so an authenticator is not added twice.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        passkey_repo: PasskeyRepoContract,
        challenge_repo: PasskeyChallengeRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._challenge_repo: PasskeyChallengeRepoContract = challenge_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PasskeyCommand) -> PasskeyRegistrationView:
        if not self._ceremony.is_available():
            raise passkeys_unavailable()

        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None:
            raise NotFoundError(f"User {input_data.user_id} was not found.")

        self._step_up.require_recent_authentication()
        refuse_more_passkeys(self._passkey_repo, user.id)
        challenge: PasskeyChallengeDocument = issue_passkey_challenge(
            self._challenge_repo,
            self._ceremony,
            self._wall_clock,
            user.id,
            PasskeyCeremonyPurpose.REGISTRATION,
        )
        return PasskeyRegistrationView(
            passkey_challenge_id=challenge.id,
            options=self._ceremony.creation_options(
                user.id,
                account_name_of(user),
                challenge.challenge,
                self._passkey_repo.list_for_user(user.id),
            ),
        )
