from babel import Locale

from app.contracts.registries import CountryRegistryContract, PlanRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog.countries import (
    CountryList,
    CountryListItem,
    CountryListRequest,
)
from app.schemas.typings.billing.booleans import HasLocalPriceBook
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.shared.subscription_pricing import select_subscription_currency
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.localization.display_names import build_country_display_name


class ListCountriesUseCase(UseCaseContract[CountryListRequest, CountryList]):
    """
    Every country a business can come from, named in the display language
    and ordered by that name, for the sign-up and onboarding country picker.
    Restricted countries stay in the list with their status so the picker
    can explain why they are unavailable. Each says whether the plans have
    explicit prices in its currency (`has_price_book`), so the landing page
    can show a visitor prices that are not conversions.
    """

    def __init__(
        self,
        country_registry: CountryRegistryContract,
        plan_registry: PlanRegistryContract,
    ) -> None:
        self._country_registry: CountryRegistryContract = country_registry
        self._plan_registry: PlanRegistryContract = plan_registry

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
                has_price_book=self._has_price_book(profile.currency_code),
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

    def _has_price_book(self, currency_code: CurrencyCode) -> HasLocalPriceBook:
        """
        Every plan is billed in this currency (the same rule subscriptions
        follow: the monthly price and the setup fee are both in the price
        book, or it is the plans' own currency).
        """

        plans = self._plan_registry.list_all()
        return plans != [] and all(
            select_subscription_currency(self._plan_registry, plan.key, currency_code)
            == currency_code
            for plan in plans
        )
