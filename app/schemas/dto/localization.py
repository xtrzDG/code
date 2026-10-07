from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LanguageVoiceSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    PhoneNumberKind,
    RecordingConsentRule,
    TextDirection,
)
from app.schemas.typings.localization.booleans import IsMobilePhoneNumber
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    EmergencyNumber,
    LanguageTag,
    ScriptCode,
    TimezoneName,
)
from app.schemas.typings.localization.strings import (
    CountryDisplayName,
    FormattedPhoneNumber,
    LanguageDisplayName,
    LocalizedTextValue,
)


class LocalizedText(ImmutableDTO):
    """
    The same text in several languages.

    Resolution falls back: requested tag -> its base language -> English ->
    any available value. English ("en") must always be present.
    """

    values: dict[LanguageTag, LocalizedTextValue]


class PhoneNumberDetails(ImmutableDTO):
    """A phone number of any country, validated against its numbering plan."""

    e164: E164PhoneNumber
    country_code: CountryCode
    calling_code: CountryCallingCode
    kind: PhoneNumberKind
    is_mobile: IsMobilePhoneNumber
    international_format: FormattedPhoneNumber
    national_format: FormattedPhoneNumber
    timezones: list[TimezoneName] = Field(default_factory=list[TimezoneName])


class CountryProfile(ImmutableDTO):
    """
    Everything that changes when a business is in another country.

    Built for every country from phonenumbers and CLDR data, then refined by
    curated overrides (emergency numbers, launch languages, recording rules).
    """

    country_code: CountryCode
    english_name: CountryDisplayName
    calling_code: CountryCallingCode
    currency_code: CurrencyCode
    timezones: list[TimezoneName]
    default_timezone: TimezoneName
    default_customer_languages: list[LanguageTag]
    on_request_customer_languages: list[LanguageTag] = Field(
        default_factory=list[LanguageTag]
    )
    default_owner_language: LanguageTag
    emergency_number: EmergencyNumber
    data_region: DataRegion
    onboarding_status: CountryOnboardingStatus
    otp_delivery_channels: list[OtpDeliveryChannel]
    local_number_provisioning: LocalNumberProvisioning
    recording_consent_rule: RecordingConsentRule = RecordingConsentRule.NOTICE


class LanguageProfile(ImmutableDTO):
    """What the assistant can do in one language."""

    tag: LanguageTag
    english_name: LanguageDisplayName
    native_name: LanguageDisplayName
    script: ScriptCode
    direction: TextDirection
    text_support: LanguageTextSupport
    voice_support: LanguageVoiceSupport
