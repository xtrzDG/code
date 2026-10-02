"""Country profiles of every region with a phone numbering plan."""

import threading
from datetime import UTC, date, datetime, timedelta

import phonenumbers
from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import CountryRegistryContract, LanguageRegistryContract
from app.registries.localization.country_facts import (
    choose_default_timezone,
    find_country_currency,
    find_country_timezones,
    find_otp_delivery_channels,
)
from app.registries.localization.country_language_choices import (
    find_customer_languages,
    find_official_languages,
    find_on_request_languages,
    find_owner_language,
)
from app.registries.localization.curated_country_telephony import (
    ALL_PARTY_CONSENT_COUNTRIES,
    CURATED_EMERGENCY_NUMBERS,
    DEFAULT_EMERGENCY_NUMBER,
    LOCAL_NUMBER_AVAILABLE_COUNTRIES,
    PILOT_COUNTRIES,
)
from app.registries.localization.territory_languages import (
    TerritoryLanguage,
    load_territory_languages,
)
from app.schemas.constants.localization import (
    CountryOnboardingStatus,
    DataRegion,
    LocalNumberProvisioning,
    RecordingConsentRule,
)
from app.schemas.dto.localization import CountryProfile
from app.schemas.exceptions.application_errors import UnknownCountryError
from app.schemas.typings.localization.constrained_integers import CountryCallingCode
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import CountryDisplayName
from app.utilities.localization.language_tags import (
    get_english_locale,
    read_locale_name,
)

UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)


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
        territory_languages: list[TerritoryLanguage] = load_territory_languages(
            region_code
        )
        official_languages: list[LanguageTag] = find_official_languages(
            self._language_registry, territory_languages
        )
        customer_languages: list[LanguageTag] = find_customer_languages(
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
            on_request_customer_languages=find_on_request_languages(
                self._language_registry,
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
