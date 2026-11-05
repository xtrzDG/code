from typed_time_provider import Microseconds, WallClock

from app.contracts.mfa import TotpSecretCipherAdapterContract
from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import TotpEnrollmentView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.mfa.totp_enrollment import begin_totp_enrollment


class StartTotpEnrollmentUseCase(UseCaseContract[UserId, TotpEnrollmentView]):
    """
    The signed-in person starts setting up an authenticator (Account →
    Security): a new pending one, shown once as a QR code and a secret.
    Like every change of how someone signs in, it needs a recent sign-in or
    confirmation (step-up). A person whose authenticator is already on
    removes it first (ConflictError).
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        totp_secret_cipher: TotpSecretCipherAdapterContract,
        step_up: StepUpGuardContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._totp_secret_cipher: TotpSecretCipherAdapterContract = totp_secret_cipher
        self._step_up: StepUpGuardContract = step_up
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UserId) -> TotpEnrollmentView:
        user: UserDocument | None = self._user_repo.get(input_data)
        if user is None:
            raise NotFoundError(f"User {input_data} was not found.")

        self._step_up.require_recent_authentication()
        return begin_totp_enrollment(
            self._totp_factor_repo,
            self._totp_secret_cipher,
            self._app_settings,
            user,
            self._wall_clock.now_unix(),
        )
