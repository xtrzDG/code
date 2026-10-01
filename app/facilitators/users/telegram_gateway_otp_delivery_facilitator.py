from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.contracts.messaging_clients import TelegramGatewayClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode


class TelegramGatewayOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """
    Login codes through the Telegram Gateway: Telegram writes the message in
    the user's Telegram language and deletes it when the code expires.
    """

    def __init__(
        self,
        gateway_client: TelegramGatewayClientContract,
        app_settings: AppSettings,
    ) -> None:
        self._gateway_client: TelegramGatewayClientContract = gateway_client
        self._app_settings: AppSettings = app_settings

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset({OtpDeliveryChannel.TELEGRAM})

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        del email, language_tag
        if delivery_channel is not OtpDeliveryChannel.TELEGRAM or phone_number is None:
            raise ExternalServiceError(
                "The Telegram Gateway only sends codes to phone numbers."
            )

        self._gateway_client.send_verification_message(
            phone_number,
            code,
            self._app_settings.otp_lifetime_seconds,
        )
