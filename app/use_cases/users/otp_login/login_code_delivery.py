"""Which channels carry a login code, and sending it through the first that works."""

import logging

from app.contracts.facilitators import OtpDeliveryFacilitatorContract
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.localization import CountryProfile
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.utilities.security.login_code_channels import (
    list_country_phone_channels,
    list_usable_phone_channels,
)

logger: logging.Logger = logging.getLogger(__name__)
# Provider details (names, settings, credentials) stay in the server log.
LOGIN_CODE_DELIVERY_FAILED_MESSAGE: str = (
    "We could not send a login code right now. Try another way to sign in "
    "or try again later."
)


def choose_phone_delivery_channels(
    otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
    country: CountryProfile,
    preferred_channel: OtpDeliveryChannel | None,
) -> list[OtpDeliveryChannel]:
    """The country's phone channels that have a provider, preferred first."""

    if not list_country_phone_channels(country):
        raise ValidationFailedError(
            "Login codes cannot be sent to phones in "
            f"{str(country.country_code)}; sign in with e-mail."
        )

    usable_channels: list[OtpDeliveryChannel] = list_usable_phone_channels(
        country, otp_delivery_facilitator.available_channels()
    )
    if not usable_channels:
        raise ExternalServiceError(
            "Login codes cannot be sent to phones in "
            f"{str(country.country_code)} right now: no SMS, WhatsApp or "
            "Telegram provider is configured for them. Sign in with e-mail."
        )

    if preferred_channel is not None and preferred_channel in usable_channels:
        usable_channels.remove(preferred_channel)
        usable_channels.insert(0, preferred_channel)

    return usable_channels


def deliver_login_code(
    otp_delivery_facilitator: OtpDeliveryFacilitatorContract,
    delivery_channels: list[OtpDeliveryChannel],
    phone_number: E164PhoneNumber | None,
    email: EmailAddress | None,
    code: OtpCode,
    locale: LanguageTag,
) -> OtpDeliveryChannel:
    """
    Send the code through the first channel whose provider accepts it.
    Provider failures are logged; the caller gets a generic message.
    """

    for delivery_channel in delivery_channels:
        try:
            otp_delivery_facilitator.deliver(
                delivery_channel=delivery_channel,
                phone_number=phone_number,
                email=email,
                code=code,
                language_tag=locale,
            )
        except ExternalServiceError as error:
            logger.warning(
                "Login code delivery by %s failed: %s",
                delivery_channel.value,
                error,
            )
            continue

        return delivery_channel

    raise ExternalServiceError(LOGIN_CODE_DELIVERY_FAILED_MESSAGE)
