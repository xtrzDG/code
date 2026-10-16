"""Country profiles: coverage, curated countries, time zones, languages, currencies."""

import phonenumbers
import pytest
from babel.numbers import get_currency_precision

from app.registries.localization.curated_country_time_and_money import (
    CURATED_DEFAULT_TIMEZONES,
)
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    RecordingConsentRule,
)
from app.schemas.exceptions.application_errors import UnknownCountryError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.utilities.localization.timezones import is_known_timezone_name
from tests.localization.builders import get_language_registry
from tests.localization.country_registry_helpers import REGISTRY, get_profile, tags


def test_every_region_with_a_numbering_plan_has_a_profile() -> None:
    profiles = REGISTRY.list_all()
    codes = [str(profile.country_code) for profile in profiles]

    assert len(profiles) >= 200
    assert set(codes) == phonenumbers.SUPPORTED_REGIONS
    assert codes == sorted(codes)
    assert "001" not in codes


def test_georgia_matches_the_concept_exactly() -> None:
    georgia = get_profile("GE")

    assert georgia.english_name == "Georgia"
    assert georgia.calling_code == 995
    assert georgia.currency_code == "GEL"
    assert georgia.timezones == [TimezoneName("Asia/Tbilisi")]
    assert georgia.default_timezone == "Asia/Tbilisi"
    assert tags(georgia.default_customer_languages) == ["ka", "ru", "en"]
    assert tags(georgia.on_request_customer_languages) == ["tr", "he", "ar", "hy"]
    assert georgia.default_owner_language == "ka"
    assert georgia.emergency_number == "112"
    assert georgia.onboarding_status is CountryOnboardingStatus.PILOT
    assert georgia.local_number_provisioning is LocalNumberProvisioning.AVAILABLE
    assert georgia.recording_consent_rule is RecordingConsentRule.NOTICE
    assert georgia.data_region is DataRegion.EU


@pytest.mark.parametrize(
    (
        "country_code",
        "currency_code",
        "default_timezone",
        "customer_languages",
        "owner_language",
        "emergency_number",
    ),
    [
        ("AM", "AMD", "Asia/Yerevan", ["hy", "ru", "en"], "hy", "112"),
        ("IL", "ILS", "Asia/Jerusalem", ["he", "en", "ru", "ar"], "he", "100"),
        ("KZ", "KZT", "Asia/Almaty", ["ru", "kk", "en"], "ru", "112"),
        ("PL", "PLN", "Europe/Warsaw", ["pl", "en"], "pl", "112"),
        ("LT", "EUR", "Europe/Vilnius", ["lt", "en", "ru"], "lt", "112"),
        ("LV", "EUR", "Europe/Riga", ["lv", "en", "ru"], "lv", "112"),
        ("EE", "EUR", "Europe/Tallinn", ["et", "en", "ru"], "et", "112"),
        ("US", "USD", "America/New_York", ["en", "es"], "en", "911"),
    ],
)
def test_expansion_countries_are_curated(
    country_code: str,
    currency_code: str,
    default_timezone: str,
    customer_languages: list[str],
    owner_language: str,
    emergency_number: str,
) -> None:
    profile = get_profile(country_code)

    assert profile.currency_code == currency_code
    assert profile.default_timezone == default_timezone
    assert tags(profile.default_customer_languages) == customer_languages
    assert profile.default_owner_language == owner_language
    assert profile.emergency_number == emergency_number
    assert profile.on_request_customer_languages != []
    assert profile.onboarding_status is CountryOnboardingStatus.SUPPORTED


@pytest.mark.parametrize(
    ("country_code", "default_timezone"),
    [
        ("US", "America/New_York"),
        ("RU", "Europe/Moscow"),
        ("BR", "America/Sao_Paulo"),
        ("KZ", "Asia/Almaty"),
        ("CA", "America/Toronto"),
        ("AU", "Australia/Sydney"),
        ("MX", "America/Mexico_City"),
        ("ID", "Asia/Jakarta"),
        ("ES", "Europe/Madrid"),
        ("UA", "Europe/Kyiv"),
    ],
)
def test_multi_zone_countries_default_to_the_business_capital(
    country_code: str,
    default_timezone: str,
) -> None:
    profile = get_profile(country_code)

    assert len(profile.timezones) > 1
    assert profile.default_timezone == default_timezone


def test_every_multi_zone_country_has_a_curated_default() -> None:
    for profile in REGISTRY.list_all():
        if len(profile.timezones) > 1:
            assert profile.country_code in CURATED_DEFAULT_TIMEZONES, (
                profile.country_code
            )


def test_every_profile_is_consistent() -> None:
    language_registry = get_language_registry()
    for profile in REGISTRY.list_all():
        assert profile.timezones != []
        assert profile.default_timezone in profile.timezones
        assert all(is_known_timezone_name(str(zone)) for zone in profile.timezones)
        assert 0 <= get_currency_precision(str(profile.currency_code)) <= 4
        assert profile.default_customer_languages != []
        assert len(profile.default_customer_languages) == len(
            set(profile.default_customer_languages)
        )
        assert not set(profile.default_customer_languages) & set(
            profile.on_request_customer_languages
        )
        for language_tag in (
            *profile.default_customer_languages,
            *profile.on_request_customer_languages,
            profile.default_owner_language,
        ):
            language_registry.get(language_tag)
        assert profile.otp_delivery_channels[:2] in (
            [OtpDeliveryChannel.SMS, OtpDeliveryChannel.WHATSAPP],
            [OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.SMS],
        )
        assert OtpDeliveryChannel.EMAIL not in profile.otp_delivery_channels
        assert profile.data_region is DataRegion.EU


def test_derived_defaults_add_english_for_tourists() -> None:
    japan = get_profile("JP")
    belgium = get_profile("BE")
    switzerland = get_profile("CH")

    assert tags(japan.default_customer_languages) == ["ja", "en"]
    assert japan.default_owner_language == "ja"
    assert tags(belgium.default_customer_languages) == ["nl", "fr", "de", "en"]
    # Curated: CLDR would offer Swiss German as an official language.
    assert tags(switzerland.default_customer_languages) == ["de", "fr", "it", "en"]


def test_right_to_left_countries_keep_their_scripts() -> None:
    israel = get_profile("IL")
    emirates = get_profile("AE")
    pakistan = get_profile("PK")

    assert "he" in tags(israel.default_customer_languages)
    assert "ar" in tags(emirates.default_customer_languages)
    assert tags(pakistan.default_customer_languages) == ["ur", "en"]


def test_regions_without_cldr_zones_use_libphonenumber() -> None:
    assert get_profile("XK").timezones == [TimezoneName("Europe/Belgrade")]
    assert get_profile("AC").timezones == [TimezoneName("Atlantic/St_Helena")]
    assert get_profile("TA").timezones == [TimezoneName("Atlantic/St_Helena")]
    assert get_profile("XK").currency_code == "EUR"


def test_currencies_follow_curated_changes_and_cldr() -> None:
    assert get_profile("BG").currency_code == "EUR"
    assert get_profile("HR").currency_code == "EUR"
    assert get_profile("PA").currency_code == "USD"
    assert get_profile("EC").currency_code == "USD"
    assert get_profile("PS").currency_code == "ILS"
    assert get_profile("JP").currency_code == "JPY"
    assert get_profile("KW").currency_code == "KWD"


@pytest.mark.parametrize("country_code", ["ZZ", "AA", "XX", "QQ"])
def test_unknown_country_codes_are_rejected(country_code: str) -> None:
    with pytest.raises(UnknownCountryError):
        REGISTRY.get(CountryCode(country_code))


def test_returned_profiles_are_independent_copies() -> None:
    profile = get_profile("GE")
    profile.default_customer_languages.append(LanguageTag("de"))
    profile.timezones.clear()

    fresh = get_profile("GE")
    assert tags(fresh.default_customer_languages) == ["ka", "ru", "en"]
    assert fresh.timezones == [TimezoneName("Asia/Tbilisi")]
