import logging

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode

logger: logging.Logger = logging.getLogger(__name__)


class LoggingOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """
    Development stand-in for SMS, WhatsApp, Telegram and e-mail delivery.

    Writes the code to the application log when code logging is enabled
    (`OTP_LOG_CODES`, on by default in development and test). Never in
    production: there it offers no channel and refuses every code. The
    provider-backed facilitators take over each channel that has a provider.
    """

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings: AppSettings = app_settings

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        if not self._is_logging_allowed():
            return frozenset()

        return frozenset(OtpDeliveryChannel)

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        if not self._is_logging_allowed():
            raise ExternalServiceError(
                "Login codes cannot be delivered: no SMS, WhatsApp, Telegram or "
                f"e-mail provider is configured (requested channel: "
                f"{delivery_channel.value})."
            )

        # No phone number or e-mail in the log line, not even masked: personal
        # data stays out of logs; the channel and language are enough to tell
        # concurrent development logins apart.
        logger.warning(
            "Login code %s via %s (language %s). Code logging is for development only.",
            code,
            delivery_channel.value,
            language_tag,
        )

    def _is_logging_allowed(self) -> bool:
        return (
            self._app_settings.is_otp_code_logging_enabled
            and self._app_settings.environment is not DeploymentEnvironment.PRODUCTION
        )
