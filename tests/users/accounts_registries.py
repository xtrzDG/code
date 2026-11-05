"""Small fake registries of countries, languages and niches for the accounts tests."""

from app.contracts.registries import (
    CountryRegistryContract,
    LanguageRegistryContract,
    NicheTemplateRegistryContract,
)
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LanguageVoiceSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    RecordingConsentRule,
    TextDirection,
)
from app.schemas.constants.niches import LaunchWave, NicheKey
from app.schemas.dto.localization import CountryProfile, LanguageProfile, LocalizedText
from app.schemas.dto.niches import NicheTemplate
from app.schemas.exceptions.application_errors import (
    NotFoundError,
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
    LocalizedTextValue,
)


def build_country(
    code: str,
    name: str,
    calling_code: int,
    currency: str,
    timezones: list[str],
    languages: list[str],
    owner_language: str,
    emergency_number: str,
    otp_channels: list[OtpDeliveryChannel],
    data_region: DataRegion = DataRegion.EU,
    status: CountryOnboardingStatus = CountryOnboardingStatus.SUPPORTED,
    recording_rule: RecordingConsentRule = RecordingConsentRule.NOTICE,
) -> CountryProfile:
    return CountryProfile(
        country_code=CountryCode(code),
        english_name=CountryDisplayName(name),
        calling_code=CountryCallingCode(calling_code),
        currency_code=CurrencyCode(currency),
        timezones=[TimezoneName(zone) for zone in timezones],
        default_timezone=TimezoneName(timezones[0]),
        default_customer_languages=[LanguageTag(tag) for tag in languages],
        default_owner_language=LanguageTag(owner_language),
        emergency_number=EmergencyNumber(emergency_number),
        data_region=data_region,
        onboarding_status=status,
        otp_delivery_channels=otp_channels,
        local_number_provisioning=LocalNumberProvisioning.AVAILABLE,
        recording_consent_rule=recording_rule,
    )


SMS: OtpDeliveryChannel = OtpDeliveryChannel.SMS


WHATSAPP: OtpDeliveryChannel = OtpDeliveryChannel.WHATSAPP


TELEGRAM: OtpDeliveryChannel = OtpDeliveryChannel.TELEGRAM


EMAIL_CHANNEL: OtpDeliveryChannel = OtpDeliveryChannel.EMAIL


COUNTRY_PROFILES: list[CountryProfile] = [
    build_country(
        "AE", "United Arab Emirates", 971, "AED", ["Asia/Dubai"],
        ["ar", "en"], "ar", "999", [WHATSAPP, SMS],
        status=CountryOnboardingStatus.PILOT,
    ),
    build_country(
        "BR", "Brazil", 55, "BRL", ["America/Sao_Paulo", "America/Manaus"],
        ["pt-BR", "en", "es"], "pt-BR", "190", [WHATSAPP, SMS],
        status=CountryOnboardingStatus.PILOT,
    ),
    build_country(
        "DE", "Germany", 49, "EUR", ["Europe/Berlin"], ["de", "en"], "de", "112",
        [SMS],
    ),
    build_country(
        "GE", "Georgia", 995, "GEL", ["Asia/Tbilisi"], ["ka", "ru", "en"], "ka",
        "112", [SMS, WHATSAPP, TELEGRAM],
    ),
    build_country(
        "IL", "Israel", 972, "ILS", ["Asia/Jerusalem"], ["he", "en", "ru", "ar"],
        "he", "100", [WHATSAPP, SMS],
    ),
    build_country(
        "IN", "India", 91, "INR", ["Asia/Kolkata"], ["hi", "en"], "en", "112",
        [SMS, WHATSAPP],
    ),
    build_country(
        "IR", "Iran", 98, "IRR", ["Asia/Tehran"], ["fa", "en"], "fa", "110", [SMS],
    ),
    build_country(
        "JP", "Japan", 81, "JPY", ["Asia/Tokyo"], ["ja", "en"], "ja", "110", [SMS],
    ),
    build_country(
        "KP", "North Korea", 850, "KPW", ["Asia/Pyongyang"], ["ko"], "ko", "119",
        [SMS], status=CountryOnboardingStatus.RESTRICTED,
    ),
    build_country(
        "MC", "Monaco", 377, "EUR", ["Europe/Monaco"], ["fr", "en"], "fr", "112",
        [EMAIL_CHANNEL],
    ),
    build_country(
        "US", "United States", 1, "USD",
        ["America/New_York", "America/Chicago", "America/Los_Angeles"],
        ["en", "es"], "en", "911", [SMS], data_region=DataRegion.US,
        status=CountryOnboardingStatus.PILOT,
        recording_rule=RecordingConsentRule.ALL_PARTY_CONSENT,
    ),
]  # fmt: skip


class FakeCountryRegistry(CountryRegistryContract):
    def __init__(self) -> None:
        self._profiles: dict[CountryCode, CountryProfile] = {
            profile.country_code: profile for profile in COUNTRY_PROFILES
        }

    def get(self, country_code: CountryCode) -> CountryProfile:
        profile: CountryProfile | None = self._profiles.get(country_code)
        if profile is None:
            raise UnknownCountryError(f"Unknown country {country_code}.")

        return profile

    def list_all(self) -> list[CountryProfile]:
        return sorted(self._profiles.values(), key=lambda profile: profile.country_code)


def build_language(
    tag: str,
    english_name: str,
    native_name: str,
    script: str,
    direction: TextDirection = TextDirection.LEFT_TO_RIGHT,
    voice_support: LanguageVoiceSupport = LanguageVoiceSupport.VERIFIED,
) -> LanguageProfile:
    return LanguageProfile(
        tag=LanguageTag(tag),
        english_name=LanguageDisplayName(english_name),
        native_name=LanguageDisplayName(native_name),
        script=ScriptCode(script),
        direction=direction,
        text_support=LanguageTextSupport.SUPPORTED,
        voice_support=voice_support,
    )


RTL: TextDirection = TextDirection.RIGHT_TO_LEFT


LANGUAGE_PROFILES: list[LanguageProfile] = [
    build_language("ar", "Arabic", "العربية", "Arab", RTL),
    build_language("de", "German", "Deutsch", "Latn"),
    build_language("en", "English", "English", "Latn"),
    build_language("es", "Spanish", "Español", "Latn"),
    build_language("fa", "Persian", "فارسی", "Arab", RTL),
    build_language("fr", "French", "Français", "Latn"),
    build_language("he", "Hebrew", "עברית", "Hebr", RTL),
    build_language("hi", "Hindi", "हिन्दी", "Deva"),
    build_language("hy", "Armenian", "Հայերեն", "Armn"),
    build_language("ja", "Japanese", "日本語", "Jpan"),
    build_language(
        "ka", "Georgian", "ქართული", "Geor",
        voice_support=LanguageVoiceSupport.NEEDS_PILOT_CHECK,
    ),
    build_language("ko", "Korean", "한국어", "Kore"),
    build_language("pt", "Portuguese", "Português", "Latn"),
    build_language("pt-BR", "Brazilian Portuguese", "Português (Brasil)", "Latn"),
    build_language("ru", "Russian", "Русский", "Cyrl"),
    build_language("tr", "Turkish", "Türkçe", "Latn"),
]  # fmt: skip


class FakeLanguageRegistry(LanguageRegistryContract):
    def __init__(self) -> None:
        self._profiles: dict[LanguageTag, LanguageProfile] = {
            profile.tag: profile for profile in LANGUAGE_PROFILES
        }

    def get(self, language_tag: LanguageTag) -> LanguageProfile:
        profile: LanguageProfile | None = self._profiles.get(language_tag)
        if profile is None:
            raise UnsupportedLanguageError(f"Unsupported language {language_tag}.")

        return profile

    def list_all(self) -> list[LanguageProfile]:
        return list(self._profiles.values())


def build_niche(key: NicheKey, recommended_plans: list[PlanKey]) -> NicheTemplate:
    text = LocalizedText(values={LanguageTag("en"): LocalizedTextValue(key.value)})
    return NicheTemplate(
        key=key,
        wave=LaunchWave.A,
        names=text,
        descriptions=text,
        recommended_plans=recommended_plans,
        resource_kind=ResourceKind.TABLE,
        booking_unit=BookingUnit.TIME_SLOT,
        resource_nouns=text,
        knowledge_kinds=[KnowledgeItemKind.FAQ],
        questions=[],
        prompt_rules=[],
        default_handoff_rules=text,
        default_forbidden_rules=text,
        autotest_kinds=[AutotestScenarioKind.BOOKING],
    )


class FakeNicheTemplateRegistry(NicheTemplateRegistryContract):
    def __init__(self) -> None:
        self._templates: dict[NicheKey, NicheTemplate] = {
            NicheKey.RESTAURANT: build_niche(
                NicheKey.RESTAURANT,
                [PlanKey.VOICE_AND_CHAT, PlanKey.CHAT],
            ),
            NicheKey.HOTEL: build_niche(NicheKey.HOTEL, [PlanKey.PLUS]),
            NicheKey.ENTERTAINMENT: build_niche(
                NicheKey.ENTERTAINMENT,
                [PlanKey.CHAT, PlanKey.VOICE_AND_CHAT],
            ),
            NicheKey.CLINIC: build_niche(NicheKey.CLINIC, []),
        }

    def get(self, niche_key: NicheKey) -> NicheTemplate:
        template: NicheTemplate | None = self._templates.get(niche_key)
        if template is None:
            raise NotFoundError(f"Niche {niche_key} has no template.")

        return template

    def list_all(self) -> list[NicheTemplate]:
        return list(self._templates.values())
