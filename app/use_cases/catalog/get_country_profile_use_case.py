from babel import Locale
from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import CountryRegistryContract, LanguageRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog.countries import (
    CountryProfileRequest,
    CountryProfileView,
    LanguageOption,
    TimezoneOption,
)
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.utilities.localization.display_names import (
    build_country_display_name,
    build_currency_display_name,
    build_language_display_name_or_tag,
)
from app.utilities.localization.language_tags import require_babel_locale
from app.utilities.localization.timezones import build_timezone_display_name


class GetCountryProfileUseCase(
    UseCaseContract[CountryProfileRequest, CountryProfileView]
):
    """
    One country's defaults (currency, time zones, languages, emergency
    number, login channels, recording rule) with every code rendered in the
    display language. Time zones show the UTC offset in force now.
    """

    def __init__(
        self,
        country_registry: CountryRegistryContract,
        language_registry: LanguageRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._country_registry: CountryRegistryContract = country_registry
        self._language_registry: LanguageRegistryContract = language_registry
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CountryProfileRequest) -> CountryProfileView:
        display_locale: Locale = require_babel_locale(input_data.display_language)
        profile: CountryProfile = self._country_registry.get(input_data.country_code)
        now: Microseconds = self._wall_clock.now_unix()

        def build_timezone_option(timezone_name: TimezoneName) -> TimezoneOption:
            return TimezoneOption(
                name=timezone_name,
                display_name=build_timezone_display_name(timezone_name, now),
            )

        def build_language_option(language_tag: LanguageTag) -> LanguageOption:
            language: LanguageProfile = self._language_registry.get(language_tag)
            return LanguageOption(
                tag=language.tag,
                display_name=build_language_display_name_or_tag(
                    language.tag,
                    display_locale,
                ),
                native_name=language.native_name,
                direction=language.direction,
            )

        return CountryProfileView(
            profile=profile,
            display_language=input_data.display_language,
            display_name=build_country_display_name(
                profile.country_code,
                display_locale,
            ),
            currency_display_name=build_currency_display_name(
                profile.currency_code,
                display_locale,
            ),
            timezones=[
                build_timezone_option(timezone_name)
                for timezone_name in profile.timezones
            ],
            default_timezone=build_timezone_option(profile.default_timezone),
            default_customer_languages=[
                build_language_option(language_tag)
                for language_tag in profile.default_customer_languages
            ],
            on_request_customer_languages=[
                build_language_option(language_tag)
                for language_tag in profile.on_request_customer_languages
            ],
            default_owner_language=build_language_option(
                profile.default_owner_language
            ),
        )
