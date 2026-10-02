"""
Country policies: emergency numbers, login channels, consent, restrictions, currency
dates.
"""

import pytest

from app.registries.localization.country_registry import CountryRegistry
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    RecordingConsentRule,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.localization.builders import (
    JUNE_2025_NANOSECONDS,
    build_wall_clock,
    get_language_registry,
)
from tests.localization.country_registry_helpers import get_profile


@pytest.mark.parametrize(
    ("country_code", "emergency_number"),
    [
        ("GE", "112"),
        ("DE", "112"),
        ("TR", "112"),
        ("US", "911"),
        ("CA", "911"),
        ("MX", "911"),
        ("GB", "999"),
        ("AU", "000"),
        ("NZ", "111"),
        ("JP", "110"),
        ("BR", "190"),
        ("IN", "112"),
        ("ZA", "10111"),
    ],
)
def test_emergency_numbers(country_code: str, emergency_number: str) -> None:
    assert get_profile(country_code).emergency_number == emergency_number


@pytest.mark.parametrize(
    ("country_code", "first_channel", "has_telegram"),
    [
        ("BR", OtpDeliveryChannel.WHATSAPP, False),
        ("IN", OtpDeliveryChannel.WHATSAPP, False),
        ("IL", OtpDeliveryChannel.WHATSAPP, False),
        ("KZ", OtpDeliveryChannel.WHATSAPP, True),
        ("GE", OtpDeliveryChannel.SMS, False),
        ("US", OtpDeliveryChannel.SMS, False),
        ("AM", OtpDeliveryChannel.SMS, True),
        ("UA", OtpDeliveryChannel.SMS, True),
    ],
)
def test_login_code_channels(
    country_code: str,
    first_channel: OtpDeliveryChannel,
    has_telegram: bool,
) -> None:
    channels = get_profile(country_code).otp_delivery_channels

    assert channels[0] is first_channel
    assert (OtpDeliveryChannel.TELEGRAM in channels) is has_telegram


def test_recording_consent_and_local_numbers() -> None:
    for country_code in ("US", "DE", "FR", "CH", "AU"):
        assert (
            get_profile(country_code).recording_consent_rule
            is RecordingConsentRule.ALL_PARTY_CONSENT
        )
    for country_code in ("GE", "IL", "GB", "CA", "PL"):
        assert (
            get_profile(country_code).recording_consent_rule
            is RecordingConsentRule.NOTICE
        )
    for country_code in ("US", "CA", "GB", "GE"):
        assert (
            get_profile(country_code).local_number_provisioning
            is LocalNumberProvisioning.AVAILABLE
        )
    assert (
        get_profile("AM").local_number_provisioning
        is LocalNumberProvisioning.REQUIRES_DOCUMENTS
    )


def test_restricted_countries_cannot_onboard_or_buy_numbers() -> None:
    for country_code in ("CU", "IR", "KP", "SY"):
        profile = get_profile(country_code)
        assert profile.onboarding_status is CountryOnboardingStatus.RESTRICTED
        assert profile.local_number_provisioning is LocalNumberProvisioning.UNAVAILABLE


def test_restrictions_and_data_region_come_from_the_constructor() -> None:
    registry = CountryRegistry(
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(),
        default_data_region=DataRegion.US,
        restricted_country_codes=[CountryCode("RU")],
    )

    assert registry.get(CountryCode("RU")).onboarding_status is (
        CountryOnboardingStatus.RESTRICTED
    )
    assert registry.get(CountryCode("IR")).onboarding_status is (
        CountryOnboardingStatus.SUPPORTED
    )
    assert registry.get(CountryCode("GE")).data_region is DataRegion.US


def test_currency_depends_on_the_clock_date() -> None:
    registry = CountryRegistry(
        language_registry=get_language_registry(),
        wall_clock=build_wall_clock(JUNE_2025_NANOSECONDS),
        default_data_region=DataRegion.EU,
        restricted_country_codes=[],
    )

    # CLDR: the Caribbean guilder (XCG) replaces the Netherlands Antillean
    # guilder (ANG) in Curacao between these two dates.
    assert registry.get(CountryCode("CW")).currency_code == "ANG"
    assert get_profile("CW").currency_code == "XCG"
    assert registry.get(CountryCode("HR")).currency_code == "EUR"
