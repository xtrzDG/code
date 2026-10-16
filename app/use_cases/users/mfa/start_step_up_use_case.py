from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import StepUpMethod, TotpFactorStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import StartStepUpCommand, StepUpChallengeView
from app.schemas.dto.users import OtpChallengeView, StartOtpLoginCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput


class StartStepUpUseCase(UseCaseContract[StartStepUpCommand, StepUpChallengeView]):
    """
    The signed-in person is about to confirm it is them before a sensitive
    action. With an authenticator, its code (or a recovery code) will do,
    and nothing is sent. Without one, a new login code goes to the phone or
    e-mail they sign in with, through the sign-in's own send (channels,
    abuse limits and caps; the user's language).
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        start_otp_login: UseCaseContract[StartOtpLoginCommand, OtpChallengeView],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._start_otp_login: UseCaseContract[
            StartOtpLoginCommand, OtpChallengeView
        ] = start_otp_login

    def run(self, input_data: StartStepUpCommand) -> StepUpChallengeView:
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None:
            raise NotFoundError(f"User {input_data.user_id} was not found.")

        factor: TotpFactorDocument | None = self._totp_factor_repo.get_for_user(user.id)
        if factor is not None and factor.status is TotpFactorStatus.ACTIVE:
            return StepUpChallengeView(method=StepUpMethod.TOTP)

        is_phone: bool = (
            user.login_method is LoginMethod.PHONE and user.phone_number is not None
        )
        login_code: OtpChallengeView = self._start_otp_login.run(
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(str(user.phone_number))
                if is_phone
                else None,
                email=RawEmailAddressInput(str(user.email))
                if not is_phone and user.email is not None
                else None,
                country_hint=user.country_code,
                locale=user.locale,
                client_ip_address=input_data.client_ip_address,
            )
        )
        return StepUpChallengeView(
            method=StepUpMethod.LOGIN_CODE, login_code=login_code
        )
