import threading
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple, cast

import phonenumbers
from babel.core import get_global
from babel.numbers import get_territory_currencies
from phonenumbers import PhoneNumber
from phonenumbers.timezone import time_zones_for_number
from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import CountryRegistryContract, LanguageRegistryContract
from app.registries.localization.curated_country_languages import (
    CURATED_CUSTOMER_LANGUAGES,
    CURATED_ON_REQUEST_LANGUAGES,
    CURATED_OWNER_LANGUAGES,
    MAX_DERIVED_OFFICIAL_LANGUAGES,
    MAX_DERIVED_ON_REQUEST_LANGUAGES,
    MIN_ON_REQUEST_POPULATION_PERCENT,
    TOURIST_LANGUAGE,
)
from app.registries.localization.curated_country_telephony import (
    ALL_PARTY_CONSENT_COUNTRIES,
    CURATED_EMERGENCY_NUMBERS,
    DEFAULT_EMERGENCY_NUMBER,
    LOCAL_NUMBER_AVAILABLE_COUNTRIES,
    PILOT_COUNTRIES,
    TELEGRAM_OTP_COUNTRIES,
    WHATSAPP_FIRST_COUNTRIES,
)
from app.registries.localization.curated_country_time_and_money import (
    CURATED_CURRENCIES,
    CURATED_DEFAULT_TIMEZONES,
    FALLBACK_CURRENCY,
    FALLBACK_TIMEZONE,
)
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LanguageTextSupport,
    LocalNumberProvisioning,
    OtpDeliveryChannel,
    RecordingConsentRule,
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
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import CountryDisplayName
from app.utilities.localization.language_tags import (
    base_language_code,
    find_babel_locale,
    get_english_locale,
    read_locale_name,
)
from app.utilities.localization.timezones import (
    is_known_timezone_name,
    list_territory_timezone_names,
)

UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
OFFICIAL_LANGUAGE_STATUSES: frozenset[str] = frozenset(
    {"official", "de_facto_official"}
)
UNKNOWN_TIMEZONE_NAME: str = "Etc/Unknown"


class _TerritoryLanguage(NamedTuple):
    """One CLDR language of a territory (a technical record of Babel data)."""

    language_tag: LanguageTag
    population_percent: float
    is_official: bool


class CountryRegistry(CountryRegistryContract):
    """
    Country profiles for every region with a phone numbering plan (245).

    Built from libphonenumber (calling codes, time zones of regions CLDR does
    not map) and CLDR via Babel (names, legal tender, time zones, languages),
    then refined by curated tables: launch languages, default time zones of
    multi-zone countries, emergency numbers, login code channels, local
    numbers and recording consent. The pilot country (Georgia) follows the
    concept exactly. Profiles are built once, on first use, with the
    currency in force on that day; callers receive independent copies.
    """

    def __init__(
        self,
        language_registry: LanguageRegistryContract,
        wall_clock: WallClock[Microseconds],
        default_data_region: DataRegion,
        restricted_country_codes: list[CountryCode],
    ) -> None:
        self._language_registry: LanguageRegistryContract = language_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._default_data_region: DataRegion = default_data_region
        self._restricted_country_codes: frozenset[CountryCode] = frozenset(
            restricted_country_codes
        )
        self._lock: threading.Lock = threading.Lock()
        self._profiles_by_code: dict[str, CountryProfile] | None = None

    def get(self, country_code: CountryCode) -> CountryProfile:
        profile: CountryProfile | None = self._load_profiles().get(str(country_code))
        if profile is None:
            raise UnknownCountryError(f"Country {country_code} is not known.")

        return copy_country_profile(profile)

    def list_all(self) -> list[CountryProfile]:
        profiles_by_code: dict[str, CountryProfile] = self._load_profiles()
        return [
            copy_country_profile(profiles_by_code[country_code])
            for country_code in sorted(profiles_by_code)
        ]

    def _load_profiles(self) -> dict[str, CountryProfile]:
        with self._lock:
            if self._profiles_by_code is None:
                currency_date: date = (
                    UNIX_EPOCH
                    + timedelta(microseconds=int(self._wall_clock.now_unix()))
                ).date()
                self._profiles_by_code = {
                    region_code: self._build_profile(region_code, currency_date)
                    for region_code in sorted(phonenumbers.SUPPORTED_REGIONS)
                }

            return self._profiles_by_code

    def _build_profile(self, region_code: str, currency_date: date) -> CountryProfile:
        country_code = CountryCode(region_code)
        timezones: list[TimezoneName] = find_country_timezones(region_code)
        territory_languages: list[_TerritoryLanguage] = load_territory_languages(
            region_code
        )
        official_languages: list[LanguageTag] = self._find_official_languages(
            territory_languages
        )
        customer_languages: list[LanguageTag] = self._find_customer_languages(
            country_code,
            official_languages,
        )
        is_restricted: bool = country_code in self._restricted_country_codes
        return CountryProfile(
            country_code=country_code,
            english_name=CountryDisplayName(
                read_locale_name(get_english_locale().territories, region_code)
                or region_code
            ),
            calling_code=CountryCallingCode(
                phonenumbers.country_code_for_region(region_code)
            ),
            currency_code=find_country_currency(country_code, currency_date),
            timezones=timezones,
            default_timezone=choose_default_timezone(country_code, timezones),
            default_customer_languages=customer_languages,
            on_request_customer_languages=self._find_on_request_languages(
                country_code,
                territory_languages,
                customer_languages,
            ),
            default_owner_language=find_owner_language(
                country_code,
                official_languages,
                customer_languages,
            ),
            emergency_number=CURATED_EMERGENCY_NUMBERS.get(
                country_code,
                DEFAULT_EMERGENCY_NUMBER,
            ),
            data_region=self._default_data_region,
            onboarding_status=(
                CountryOnboardingStatus.RESTRICTED
                if is_restricted
                else CountryOnboardingStatus.PILOT
                if country_code in PILOT_COUNTRIES
                else CountryOnboardingStatus.SUPPORTED
            ),
            otp_delivery_channels=find_otp_delivery_channels(country_code),
            local_number_provisioning=(
                LocalNumberProvisioning.UNAVAILABLE
                if is_restricted
                else LocalNumberProvisioning.AVAILABLE
                if country_code in LOCAL_NUMBER_AVAILABLE_COUNTRIES
                else LocalNumberProvisioning.REQUIRES_DOCUMENTS
            ),
            recording_consent_rule=(
                RecordingConsentRule.ALL_PARTY_CONSENT
                if country_code in ALL_PARTY_CONSENT_COUNTRIES
                else RecordingConsentRule.NOTICE
            ),
        )

    def _find_official_languages(
        self,
        territory_languages: list[_TerritoryLanguage],
    ) -> list[LanguageTag]:
        """Official languages with CLDR locale data, one per language subtag."""

        official_languages: list[LanguageTag] = []
        for territory_language in territory_languages:
            if not territory_language.is_official:
                continue

            if self._find_language_profile(territory_language.language_tag) is None:
                continue

            if find_babel_locale(territory_language.language_tag) is None:
                continue

            official_languages = append_new_language(
                official_languages,
                territory_language.language_tag,
            )

        return official_languages

    def _find_customer_languages(
        self,
        country_code: CountryCode,
        official_languages: list[LanguageTag],
    ) -> list[LanguageTag]:
        curated_languages: tuple[LanguageTag, ...] | None = (
            CURATED_CUSTOMER_LANGUAGES.get(country_code)
        )
        if curated_languages is not None:
            return list(curated_languages)

        customer_languages: list[LanguageTag] = official_languages[
            :MAX_DERIVED_OFFICIAL_LANGUAGES
        ]
        return append_new_language(customer_languages, TOURIST_LANGUAGE)

    def _find_on_request_languages(
        self,
        country_code: CountryCode,
        territory_languages: list[_TerritoryLanguage],
        customer_languages: list[LanguageTag],
    ) -> list[LanguageTag]:
        """Large resident languages the assistant writes well, not yet default."""

        curated_languages: tuple[LanguageTag, ...] | None = (
            CURATED_ON_REQUEST_LANGUAGES.get(country_code)
        )
        if curated_languages is not None:
            return list(curated_languages)

        on_request_languages: list[LanguageTag] = []
        for territory_language in territory_languages:
            if len(on_request_languages) >= MAX_DERIVED_ON_REQUEST_LANGUAGES:
                break

            if (
                territory_language.is_official
                or territory_language.population_percent
                < MIN_ON_REQUEST_POPULATION_PERCENT
            ):
                continue

            profile: LanguageProfile | None = self._find_language_profile(
                territory_language.language_tag
            )
            if profile is None or profile.text_support is not (
                LanguageTextSupport.SUPPORTED
            ):
                continue

            if has_language(customer_languages, profile.tag):
                continue

            on_request_languages = append_new_language(
                on_request_languages,
                profile.tag,
            )

        return on_request_languages

    def _find_language_profile(
        self,
        language_tag: LanguageTag,
    ) -> LanguageProfile | None:
        try:
            return self._language_registry.get(language_tag)
        except UnsupportedLanguageError:
            return None


def copy_country_profile(profile: CountryProfile) -> CountryProfile:
    """Copy whose lists can be changed without touching the cached profile."""

    return profile.model_copy(
        update={
            "timezones": list(profile.timezones),
            "default_customer_languages": list(profile.default_customer_languages),
            "on_request_customer_languages": list(
                profile.on_request_customer_languages
            ),
            "otp_delivery_channels": list(profile.otp_delivery_channels),
        }
    )


def load_territory_languages(region_code: str) -> list[_TerritoryLanguage]:
    """CLDR languages of a territory, most spoken first."""

    raw_languages: object = get_global("territory_languages").get(region_code)
    if not isinstance(raw_languages, Mapping):
        return []

    territory_languages: list[_TerritoryLanguage] = []
    for raw_language_code, raw_details in cast(
        Mapping[object, object],
        raw_languages,
    ).items():
        if not isinstance(raw_language_code, str) or not isinstance(
            raw_details,
            Mapping,
        ):
            continue

        details: Mapping[object, object] = cast(Mapping[object, object], raw_details)
        try:
            language_tag = LanguageTag(raw_language_code.replace("_", "-"))
        except ValueError:
            continue

        population_percent: object = details.get("population_percent")
        territory_languages.append(
            _TerritoryLanguage(
                language_tag=language_tag,
                population_percent=(
                    float(population_percent)
                    if isinstance(population_percent, int | float)
                    else 0.0
                ),
                is_official=details.get("official_status")
                in OFFICIAL_LANGUAGE_STATUSES,
            )
        )

    return sorted(
        territory_languages,
        key=lambda territory_language: -territory_language.population_percent,
    )


def find_country_currency(
    country_code: CountryCode, currency_date: date
) -> CurrencyCode:
    curated_currency: CurrencyCode | None = CURATED_CURRENCIES.get(country_code)
    if curated_currency is not None:
        return curated_currency

    for currency_code in get_territory_currencies(
        str(country_code),
        start_date=currency_date,
        tender=True,
    ):
        try:
            return CurrencyCode(currency_code)
        except ValueError:
            continue

    return FALLBACK_CURRENCY


def find_country_timezones(region_code: str) -> list[TimezoneName]:
    """CLDR zones of a region; libphonenumber zones where CLDR has none."""

    timezones: list[TimezoneName] = list_territory_timezone_names(region_code)
    if timezones != []:
        return timezones

    example_number: PhoneNumber | None = phonenumbers.example_number(region_code)
    if example_number is not None:
        timezones = [
            TimezoneName(zone_name)
            for zone_name in sorted(set(time_zones_for_number(example_number)))
            if zone_name != UNKNOWN_TIMEZONE_NAME and is_known_timezone_name(zone_name)
        ]

    return timezones if timezones != [] else [FALLBACK_TIMEZONE]


def choose_default_timezone(
    country_code: CountryCode,
    timezones: list[TimezoneName],
) -> TimezoneName:
    curated_timezone: TimezoneName | None = CURATED_DEFAULT_TIMEZONES.get(country_code)
    if curated_timezone is not None and curated_timezone in timezones:
        return curated_timezone

    return timezones[0]


def find_owner_language(
    country_code: CountryCode,
    official_languages: list[LanguageTag],
    customer_languages: list[LanguageTag],
) -> LanguageTag:
    curated_language: LanguageTag | None = CURATED_OWNER_LANGUAGES.get(country_code)
    if curated_language is not None:
        return curated_language

    if official_languages != []:
        return official_languages[0]

    return customer_languages[0] if customer_languages != [] else TOURIST_LANGUAGE


def find_otp_delivery_channels(country_code: CountryCode) -> list[OtpDeliveryChannel]:
    otp_delivery_channels: list[OtpDeliveryChannel] = (
        [OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.SMS]
        if country_code in WHATSAPP_FIRST_COUNTRIES
        else [OtpDeliveryChannel.SMS, OtpDeliveryChannel.WHATSAPP]
    )
    if country_code in TELEGRAM_OTP_COUNTRIES:
        otp_delivery_channels.append(OtpDeliveryChannel.TELEGRAM)

    return otp_delivery_channels


def has_language(language_tags: list[LanguageTag], language_tag: LanguageTag) -> bool:
    """True when a tag with the same language subtag is already in the list."""

    language_code: str = base_language_code(language_tag)
    return any(
        base_language_code(listed_tag) == language_code for listed_tag in language_tags
    )


def append_new_language(
    language_tags: list[LanguageTag],
    language_tag: LanguageTag,
) -> list[LanguageTag]:
    if has_language(language_tags, language_tag):
        return language_tags

    return [*language_tags, language_tag]
