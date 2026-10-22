"""The owner looks for a number: country, kind, and optionally a city."""

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import (
    PhoneNumberCountryRegistryContract,
    PhoneNumberProvisionerAdapterContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.phone_numbers import PhoneNumberAvailability
from app.schemas.constants.spend import OwnerAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.billing import Money
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneNumberOfferList,
    PhoneNumberOfferQuery,
)
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberSearchQuery,
    PhoneNumberSearchResult,
)
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.telephony.constrained_integers import PhoneNumberOfferCount
from app.use_cases.channels.phone_numbers.phone_line_lookups import quote_owner_price
from app.use_cases.channels.phone_numbers.phone_line_views import build_offer_view
from app.use_cases.shared.subscription_pricing import quote_money

OFFER_COUNT: PhoneNumberOfferCount = PhoneNumberOfferCount(10)


class SearchPhoneNumbersUseCase(
    UseCaseContract[PhoneNumberOfferQuery, PhoneNumberOfferList]
):
    """
    The owner's number search. A country whose regulator wants the
    business's documents (`PhoneNumberCountryRegistry`) offers nothing:
    REQUIRES_DOCUMENTS, the team arranges it. So does a server that rents no
    numbers by itself, or a kind the carrier does not price there:
    ON_REQUEST. Otherwise up to ten numbers that take calls and need no
    papers, near the city when one is given, at the owner's monthly price
    (the carrier's with the platform's markup, in the business's currency,
    rounded up to a whole unit).

    Searches ask the carrier's API, so a business runs 30 an hour
    (`owner_action_limits`; RateLimitedError with Retry-After).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        phone_number_provisioner: PhoneNumberProvisionerAdapterContract,
        phone_number_country_registry: PhoneNumberCountryRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        admit_owner_action: UseCaseContract[OwnerActionAdmission, None],
        app_settings: AppSettings,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._provisioner: PhoneNumberProvisionerAdapterContract = (
            phone_number_provisioner
        )
        self._country_registry: PhoneNumberCountryRegistryContract = (
            phone_number_country_registry
        )
        self._exchange_rate_registry: ExchangeRateRegistryContract = (
            exchange_rate_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._admit_owner_action: UseCaseContract[OwnerActionAdmission, None] = (
            admit_owner_action
        )
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: PhoneNumberOfferQuery) -> PhoneNumberOfferList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        availability: PhoneNumberAvailability = self._country_registry.get_availability(
            input_data.country_code, input_data.number_type
        )
        if availability is not PhoneNumberAvailability.SELF_SERVE:
            return self._without_offers(input_data, availability)

        if self._provisioner.list_missing_settings() != []:
            return self._without_offers(input_data, PhoneNumberAvailability.ON_REQUEST)

        self._admit_owner_action.run(
            OwnerActionAdmission(
                action=OwnerAction.PHONE_NUMBER_SEARCH,
                user_id=input_data.user_id,
                business_id=business.id,
            )
        )
        result: PhoneNumberSearchResult = self._provisioner.search_numbers(
            PhoneNumberSearchQuery(
                country_code=input_data.country_code,
                number_type=input_data.number_type,
                city=input_data.city,
                limit=OFFER_COUNT,
            )
        )
        if result.monthly_cost_micro_usd is None:
            return self._without_offers(input_data, PhoneNumberAvailability.ON_REQUEST)

        price: Money = quote_owner_price(
            result.monthly_cost_micro_usd,
            self._app_settings.phone_numbers,
            business.currency_code,
            self._exchange_rate_registry,
        )
        language: LanguageTag = input_data.display_language or business.owner_language
        return PhoneNumberOfferList(
            country_code=input_data.country_code,
            number_type=input_data.number_type,
            availability=PhoneNumberAvailability.SELF_SERVE,
            monthly_price=quote_money(price, False, language),
            offers=[
                build_offer_view(offer, self._phone_number_parser)
                for offer in result.numbers
            ],
        )

    def _without_offers(
        self,
        query: PhoneNumberOfferQuery,
        availability: PhoneNumberAvailability,
    ) -> PhoneNumberOfferList:
        return PhoneNumberOfferList(
            country_code=query.country_code,
            number_type=query.number_type,
            availability=availability,
        )
