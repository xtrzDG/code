from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.mfa_repositories import TotpFactorRepoContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.mfa import StepUpMethod
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.mfa import StartStepUpCommand, StepUpChallengeView
from app.schemas.dto.users import OtpChallengeView, StartOtpLoginCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.use_cases.shared.second_factors import (
    has_active_authenticator,
    has_second_factor,
    usable_passkeys,
)


class StartStepUpUseCase(UseCaseContract[StartStepUpCommand, StepUpChallengeView]):
    """
    The signed-in person is about to confirm it is them before a sensitive
    action. With an authenticator, its code (or a recovery code) will do,
    and nothing is sent; a passkey too (`passkey_available`). With passkeys
    and no authenticator, a passkey or a recovery code will do (PASSKEY),
    or only a recovery code while none of their passkeys can sign here
    (RECOVERY_CODE); nothing is sent, and a request for a login code is
    not honoured: a code at the mailbox or phone must never stand in for
    the second factor (it would let a stolen session swap the passkeys).
    Only a person with no second factor gets a new login code, at the
    phone or e-mail they sign in with, through the sign-in's own send
    (channels, abuse limits and caps; the user's language); confirming
    with it alone counts as one factor.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        totp_factor_repo: TotpFactorRepoContract,
        start_otp_login: UseCaseContract[StartOtpLoginCommand, OtpChallengeView],
        passkey_repo: PasskeyRepoContract,
        passkey_ceremony: PasskeyCeremonyAdapterContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._totp_factor_repo: TotpFactorRepoContract = totp_factor_repo
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._passkey_ceremony: PasskeyCeremonyAdapterContract = passkey_ceremony
        self._start_otp_login: UseCaseContract[
            StartOtpLoginCommand, OtpChallengeView
        ] = start_otp_login

    def run(self, input_data: StartStepUpCommand) -> StepUpChallengeView:
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None:
            raise NotFoundError(f"User {input_data.user_id} was not found.")

        has_passkey: bool = self._passkey_ceremony.is_available() and bool(
            usable_passkeys(self._passkey_repo, user.id)
        )
        if has_active_authenticator(self._totp_factor_repo, user.id):
            return StepUpChallengeView(
                method=StepUpMethod.TOTP, passkey_available=has_passkey
            )

        if has_passkey:
            return StepUpChallengeView(
                method=StepUpMethod.PASSKEY,
                passkey_available=True,
            )

        if has_second_factor(self._totp_factor_repo, self._passkey_repo, user.id):
            # Passkeys that cannot sign now (suspended, or no relying party).
            return StepUpChallengeView(method=StepUpMethod.RECOVERY_CODE)

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
            method=StepUpMethod.LOGIN_CODE,
            login_code=login_code,
            passkey_available=has_passkey,
        )
