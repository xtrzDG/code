"""Which channels can carry a login code: the country's list and the providers."""

from collections.abc import Collection

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    OtpDeliveryChannel,
)
from app.schemas.dto.localization import CountryProfile

# Channels that deliver a code to a phone number, in the default order.
PHONE_DELIVERY_CHANNELS: tuple[OtpDeliveryChannel, ...] = (
    OtpDeliveryChannel.SMS,
    OtpDeliveryChannel.WHATSAPP,
    OtpDeliveryChannel.TELEGRAM,
)


def list_country_phone_channels(country: CountryProfile) -> list[OtpDeliveryChannel]:
    """The phone channels the country's numbers can receive codes by, in order."""

    return [
        channel
        for channel in country.otp_delivery_channels
        if channel in PHONE_DELIVERY_CHANNELS
    ]


def list_usable_phone_channels(
    country: CountryProfile,
    available_channels: Collection[OtpDeliveryChannel],
) -> list[OtpDeliveryChannel]:
    """
    The country's phone channels that have a configured provider right now,
    in the country's order.
    """

    return [
        channel
        for channel in list_country_phone_channels(country)
        if channel in available_channels
    ]


def is_sign_up_restricted(country: CountryProfile, app_settings: AppSettings) -> bool:
    """Accounts cannot be created or used from this country."""

    return (
        country.onboarding_status is CountryOnboardingStatus.RESTRICTED
        or country.country_code in app_settings.restricted_country_codes
    )
