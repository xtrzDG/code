from babel import Locale

from app.contracts.registries import CountryRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog.countries import (
    CountryList,
    CountryListItem,
    CountryListRequest,
)
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.localization.display_names import build_country_display_name


class ListCountriesUseCase(UseCaseContract[CountryListRequest, CountryList]):
    """
    Every country a business can come from, named in the display language
    and ordered by that name, for the sign-up and onboarding country picker.
    Restricted countries stay in the list with their status so the picker
    can explain why they are unavailable.
    """

    def __init__(self, country_registry: CountryRegistryContract) -> None:
        self._country_registry: CountryRegistryContract = country_registry

    def run(self, input_data: CountryListRequest) -> CountryList:
        display_locale: Locale = require_babel_locale(input_data.display_language)
        countries: list[CountryListItem] = [
            CountryListItem(
                country_code=profile.country_code,
                display_name=build_country_display_name(
                    profile.country_code,
                    display_locale,
                ),
                english_name=profile.english_name,
                calling_code=profile.calling_code,
                currency_code=profile.currency_code,
                default_timezone=profile.default_timezone,
                default_owner_language=profile.default_owner_language,
                onboarding_status=profile.onboarding_status,
            )
            for profile in self._country_registry.list_all()
        ]
        return CountryList(
            display_language=input_data.display_language,
            countries=sorted(
                countries,
                key=lambda country: (
                    country.display_name.casefold(),
                    str(country.country_code),
                ),
            ),
        )
