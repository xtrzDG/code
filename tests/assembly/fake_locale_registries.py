"""Country and language registries holding the few profiles the tests use."""

from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
)
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LanguageVoiceSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    TextDirection,
)
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.exceptions.application_errors import (
    UnknownCountryError,
    UnsupportedLanguageError,
)
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    EmergencyNumber,
    LanguageTag,
    ScriptCode,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    LanguageDisplayName,
)


def build_country(
    country_code: str,
    english_name: str,
    calling_code: int,
    currency_code: str,
    timezone_name: str,
    languages: list[str],
    emergency_number: str,
) -> CountryProfile:
    return CountryProfile(
        country_code=CountryCode(country_code),
        english_name=CountryDisplayName(english_name),
        calling_code=CountryCallingCode(calling_code),
        currency_code=CurrencyCode(currency_code),
        timezones=[TimezoneName(timezone_name)],
        default_timezone=TimezoneName(timezone_name),
        default_customer_languages=[LanguageTag(tag) for tag in languages],
        default_owner_language=LanguageTag(languages[0]),
        emergency_number=EmergencyNumber(emergency_number),
        data_region=DataRegion.EU,
        onboarding_status=CountryOnboardingStatus.SUPPORTED,
        otp_delivery_channels=[OtpDeliveryChannel.SMS],
        local_number_provisioning=LocalNumberProvisioning.AVAILABLE,
    )


class FakeCountryRegistry(CountryRegistryContract):
    """Georgia, Italy, Japan, Israel and the United States."""

    def __init__(self) -> None:
        countries: list[CountryProfile] = [
            build_country("GE", "Georgia", 995, "GEL", "Asia/Tbilisi", ["ka"], "112"),
            build_country("IT", "Italy", 39, "EUR", "Europe/Rome", ["it"], "112"),
            build_country("JP", "Japan", 81, "JPY", "Asia/Tokyo", ["ja"], "110"),
            build_country("IL", "Israel", 972, "ILS", "Asia/Jerusalem", ["he"], "100"),
            build_country(
                "US", "United States", 1, "USD", "America/New_York", ["en"], "911"
            ),
        ]
        self._countries: dict[str, CountryProfile] = {
            str(country.country_code): country for country in countries
        }

    def get(self, country_code: CountryCode) -> CountryProfile:
        country: CountryProfile | None = self._countries.get(str(country_code))
        if country is None:
            raise UnknownCountryError(f"Unknown country {country_code}.")

        return country

    def list_all(self) -> list[CountryProfile]:
        return list(self._countries.values())


def build_language(
    tag: str,
    english_name: str,
    native_name: str,
    script: str,
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT,
) -> LanguageProfile:
    return LanguageProfile(
        tag=LanguageTag(tag),
        english_name=LanguageDisplayName(english_name),
        native_name=LanguageDisplayName(native_name),
        script=ScriptCode(script),
        direction=direction,
        text_support=LanguageTextSupport.SUPPORTED,
        voice_support=LanguageVoiceSupport.VERIFIED,
    )


class FakeLanguageRegistry(LanguageRegistryContract):
    """A handful of languages in Latin, Georgian, Cyrillic, Hebrew, Arabic, Japanese."""

    def __init__(self) -> None:
        languages: list[LanguageProfile] = [
            build_language("ka", "Georgian", "ქართული", "Geor"),
            build_language("ru", "Russian", "русский", "Cyrl"),
            build_language("en", "English", "English", "Latn"),
            build_language("it", "Italian", "italiano", "Latn"),
            build_language("ja", "Japanese", "日本語", "Jpan"),
            build_language(
                "he", "Hebrew", "עברית", "Hebr", TextDirection.RIGHT_TO_LEFT
            ),
            build_language(
                "ar", "Arabic", "العربية", "Arab", TextDirection.RIGHT_TO_LEFT
            ),
        ]
        self._languages: dict[str, LanguageProfile] = {
            str(language.tag): language for language in languages
        }

    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        language: LanguageProfile | None = self._languages.get(str(language_tag))
        if language is None:
            raise UnsupportedLanguageError(f"Unknown language {language_tag}.")

        return language

    def list_all(self) -> list[LanguageProfile]:
        return list(self._languages.values())
