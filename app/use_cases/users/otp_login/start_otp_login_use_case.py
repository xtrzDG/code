"""Send a login code to a phone or an e-mail address."""

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.login_protection import HighCostPhoneNumberRegistryContract
from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
)
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import (
    OtpDeliveryChannel,
    PhoneNumberKind,
)
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import OtpChallengeDocument, UserDocument
from app.schemas.dto.localization import CountryProfile, PhoneNumberDetails
from app.schemas.dto.login_protection import (
    LoginCodeDestination,
    SendLoginCodeCommand,
)
from app.schemas.dto.users import OtpChallengeView, StartOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import MaskedLoginDestination
from app.use_cases.users.otp_login.login_code_delivery import (
    choose_phone_delivery_channels,
)
from app.utilities.security.email_addresses import parse_email_address
from app.utilities.security.login_code_channels import is_sign_up_restricted
from app.utilities.security.login_destination_masking import (
    mask_email_address,
    mask_phone_number,
)

FALLBACK_LANGUAGE: LanguageTag = LanguageTag("en")
# Lines that cannot receive a text message with the code.
NON_MESSAGING_PHONE_KINDS: frozenset[PhoneNumberKind] = frozenset(
    {PhoneNumberKind.FIXED_LINE, PhoneNumberKind.TOLL_FREE}
)
CANNOT_RECEIVE_CODES_MESSAGE: str = (
    "This number cannot receive login codes; use a mobile number."
)


class StartOtpLoginUseCase(UseCaseContract[StartOtpLoginCommand, OtpChallengeView]):
    """
    Send a one-time login code to a phone number of any country or an e-mail.

    The phone's country decides whether sign-up is allowed and which channels
    can carry the code (SMS, WhatsApp, Telegram, in its order); only channels
    with a configured provider are used. The requested channel goes first
    when it is one of them; when a provider fails, the same code goes
    through the next channel of the list. E-mail login needs an e-mail
    provider. The code message (and a new account) uses the requested
    language, else the country's owner language, else English. Only a keyed
    hash of the code is stored.

    Every code is a paid message: high-cost numbers (premium rate, shared
    cost, satellite, denied ranges) never get one, and `send_login_code`
    applies the bot check, the send limits and the platform caps (codes for
    verified users' phones and e-mails have a budget of their own).
    """

    def __init__(
        self,
        phone_number_parser: PhoneNumberParserContract,
        country_registry: CountryRegistryContract,
        language_registry: LanguageRegistryContract,
        otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
        app_settings: AppSettings,
        user_repo: UserRepoContract,
        high_cost_phone_registry: HighCostPhoneNumberRegistryContract,
        send_login_code: UseCaseContract[SendLoginCodeCommand, OtpChallengeDocument],
    ) -> None:
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._country_registry: CountryRegistryContract = country_registry
        self._language_registry: LanguageRegistryContract = language_registry
        self._otp_delivery_facilitator: OtpDeliveryFacilitatorContract = (
            otp_delivery_facilitator
        )
        self._app_settings: AppSettings = app_settings
        self._user_repo: UserRepoContract = user_repo
        self._high_cost_phone_registry: HighCostPhoneNumberRegistryContract = (
            high_cost_phone_registry
        )
        self._send_login_code: UseCaseContract[
            SendLoginCodeCommand, OtpChallengeDocument
        ] = send_login_code

    def run(self, input_data: StartOtpLoginCommand) -> OtpChallengeView:
        if input_data.locale is not None:
            self._language_registry.get(input_data.locale)

        if input_data.phone_number is not None and input_data.email is None:
            phone_number: PhoneNumberDetails = self._phone_number_parser.parse(
                input_data.phone_number,
                input_data.country_hint,
            )
            return self._start_phone_login(input_data, phone_number)

        if input_data.email is not None and input_data.phone_number is None:
            email: EmailAddress = parse_email_address(input_data.email)
            return self._start_email_login(input_data, email)

        raise ValidationFailedError("Enter either a phone number or an e-mail.")

    def _start_phone_login(
        self,
        input_data: StartOtpLoginCommand,
        phone_number: PhoneNumberDetails,
    ) -> OtpChallengeView:
        if phone_number.kind in NON_MESSAGING_PHONE_KINDS or (
            self._high_cost_phone_registry.is_high_cost(phone_number.e164)
        ):
            raise ValidationFailedError(CANNOT_RECEIVE_CODES_MESSAGE)

        country: CountryProfile = self._load_allowed_country(phone_number.country_code)
        delivery_channels: list[OtpDeliveryChannel] = choose_phone_delivery_channels(
            self._otp_delivery_facilitator,
            country,
            input_data.preferred_delivery_channel,
        )
        locale: LanguageTag = input_data.locale or country.default_owner_language
        user: UserDocument | None = self._user_repo.find_by_phone_number(
            phone_number.e164
        )
        challenge: OtpChallengeDocument = self._send_login_code.run(
            SendLoginCodeCommand(
                destination=LoginCodeDestination(
                    login_method=LoginMethod.PHONE,
                    phone_number=phone_number.e164,
                    country_code=phone_number.country_code,
                    requested_channel=input_data.preferred_delivery_channel,
                    client_ip_address=input_data.client_ip_address,
                    is_verified_destination=user is not None and user.is_verified,
                ),
                delivery_channels=delivery_channels,
                locale=locale,
                turnstile_token=input_data.turnstile_token,
            )
        )
        return OtpChallengeView(
            challenge_id=challenge.id,
            login_method=LoginMethod.PHONE,
            delivery_channel=challenge.delivery_channel,
            masked_destination=mask_phone_number(phone_number),
            expires_in_seconds=self._app_settings.otp_lifetime_seconds,
            locale=locale,
            phone_number=phone_number.e164,
            international_phone_number=phone_number.international_format,
            country_code=phone_number.country_code,
        )

    def _start_email_login(
        self,
        input_data: StartOtpLoginCommand,
        email: EmailAddress,
    ) -> OtpChallengeView:
        if (
            OtpDeliveryChannel.EMAIL
            not in self._otp_delivery_facilitator.available_channels()
        ):
            raise ExternalServiceError(
                "Sign-in by e-mail is not available: no e-mail provider is "
                "configured. Sign in with a phone number."
            )

        locale: LanguageTag = input_data.locale or FALLBACK_LANGUAGE
        if input_data.country_hint is not None:
            country: CountryProfile = self._load_allowed_country(
                input_data.country_hint
            )
            locale = input_data.locale or country.default_owner_language

        masked_destination: MaskedLoginDestination = mask_email_address(email)
        user: UserDocument | None = self._user_repo.find_by_email(email)
        challenge: OtpChallengeDocument = self._send_login_code.run(
            SendLoginCodeCommand(
                destination=LoginCodeDestination(
                    login_method=LoginMethod.EMAIL,
                    email=email,
                    country_code=input_data.country_hint,
                    client_ip_address=input_data.client_ip_address,
                    is_verified_destination=user is not None and user.is_verified,
                ),
                delivery_channels=[OtpDeliveryChannel.EMAIL],
                locale=locale,
                turnstile_token=input_data.turnstile_token,
            )
        )
        return OtpChallengeView(
            challenge_id=challenge.id,
            login_method=LoginMethod.EMAIL,
            delivery_channel=OtpDeliveryChannel.EMAIL,
            masked_destination=masked_destination,
            expires_in_seconds=self._app_settings.otp_lifetime_seconds,
            locale=locale,
            country_code=input_data.country_hint,
        )

    def _load_allowed_country(self, country_code: CountryCode) -> CountryProfile:
        country: CountryProfile = self._country_registry.get(country_code)
        if is_sign_up_restricted(country, self._app_settings):
            raise CountryRestrictedError(
                f"Sign-up is not available in country {str(country_code)}."
            )

        return country
