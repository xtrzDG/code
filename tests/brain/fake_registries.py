"""A small country registry for tests: only what the brain reads from it."""

from app.contracts.registries import CountryRegistryContract
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    RecordingConsentRule,
)
from app.schemas.dto.localization import CountryProfile
from app.schemas.exceptions.application_errors import UnknownCountryError
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    EmergencyNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import CountryDisplayName

# country -> (calling code, currency, time zone, language, consent rule)
COUNTRIES: dict[str, tuple[int, str, str, str, RecordingConsentRule]] = {
    "GE": (995, "GEL", "Asia/Tbilisi", "ka", RecordingConsentRule.NOTICE),
    "IL": (972, "ILS", "Asia/Jerusalem", "he", RecordingConsentRule.NOTICE),
    "AM": (374, "AMD", "Asia/Yerevan", "hy", RecordingConsentRule.NOTICE),
    "BR": (55, "BRL", "America/Sao_Paulo", "pt", RecordingConsentRule.NOTICE),
    "DE": (49, "EUR", "Europe/Berlin", "de", RecordingConsentRule.ALL_PARTY_CONSENT),
    "US": (1, "USD", "America/New_York", "en", RecordingConsentRule.ALL_PARTY_CONSENT),
}


class FixedCountryRegistry(CountryRegistryContract):
    def get(self, country_code: CountryCode) -> CountryProfile:
        details = COUNTRIES.get(str(country_code))
        if details is None:
            raise UnknownCountryError(f"Country {country_code} is not known.")

        calling_code, currency, timezone, language, consent_rule = details
        return CountryProfile(
            country_code=country_code,
            english_name=CountryDisplayName(str(country_code)),
            calling_code=CountryCallingCode(calling_code),
            currency_code=CurrencyCode(currency),
            timezones=[TimezoneName(timezone)],
            default_timezone=TimezoneName(timezone),
            default_customer_languages=[LanguageTag(language), LanguageTag("en")],
            default_owner_language=LanguageTag(language),
            emergency_number=EmergencyNumber("112"),
            data_region=DataRegion.EU,
            onboarding_status=CountryOnboardingStatus.SUPPORTED,
            otp_delivery_channels=[OtpDeliveryChannel.SMS],
            local_number_provisioning=LocalNumberProvisioning.AVAILABLE,
            recording_consent_rule=consent_rule,
        )

    def list_all(self) -> list[CountryProfile]:
        return [self.get(CountryCode(code)) for code in sorted(COUNTRIES)]


FIXED_COUNTRY_REGISTRY = FixedCountryRegistry()
