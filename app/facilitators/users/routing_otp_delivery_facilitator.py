from collections.abc import Mapping

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode


class RoutingOtpDeliveryFacilitator(OtpDeliveryFacilitatorContract):
    """
    Sends each login code through the provider configured for its channel
    (SMS: Twilio, Telegram: Telegram Gateway, WhatsApp: authentication
    template, e-mail: SMTP). Channels without a provider are not available;
    StartOtpLoginUseCase only picks available channels.
    """

    def __init__(
        self,
        providers: Mapping[OtpDeliveryChannel, OtpDeliveryFacilitatorContract],
    ) -> None:
        self._providers: dict[OtpDeliveryChannel, OtpDeliveryFacilitatorContract] = (
            dict(providers)
        )

    def available_channels(self) -> frozenset[OtpDeliveryChannel]:
        return frozenset(self._providers)

    def deliver(
        self,
        delivery_channel: OtpDeliveryChannel,
        phone_number: E164PhoneNumber | None,
        email: EmailAddress | None,
        code: OtpCode,
        language_tag: LanguageTag,
    ) -> None:
        provider: OtpDeliveryFacilitatorContract | None = self._providers.get(
            delivery_channel
        )
        if provider is None:
            raise ExternalServiceError(
                f"Login codes by {delivery_channel.value} are not available: no "
                "provider is configured for this channel."
            )

        provider.deliver(
            delivery_channel=delivery_channel,
            phone_number=phone_number,
            email=email,
            code=code,
            language_tag=language_tag,
        )
