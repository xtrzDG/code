from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.messaging_clients import SmsMessagingClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.security.login_code_texts import (
    LOGIN_CODE_SMS,
    fill_login_code_text,
    lifetime_in_minutes,
)


class SmsOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """Login codes by SMS, in the user's language (English as the fallback)."""

    def __init__(
        self,
        sms_client: SmsMessagingClientContract,
        localized_text_resolver: LocalizedTextResolverContract,
        app_settings: AppSettings,
    ) -> None:
        self._sms_client: SmsMessagingClientContract = sms_client
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )
        self._app_settings: AppSettings = app_settings

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset({OtpDeliveryChannel.SMS})

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        del email
        if delivery_channel is not OtpDeliveryChannel.SMS or phone_number is None:
            raise ExternalServiceError("The SMS provider only sends codes to phones.")

        text: str = fill_login_code_text(
            self._localized_text_resolver.resolve(LOGIN_CODE_SMS, language_tag),
            code,
            lifetime_in_minutes(self._app_settings.otp_lifetime_seconds),
        )
        self._sms_client.send_sms(phone_number, SmsMessageText(text))
