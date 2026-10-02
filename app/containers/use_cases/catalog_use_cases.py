from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog import (
    CallForwardingInstructions,
    CallForwardingInstructionsQuery,
    CountryList,
    CountryListRequest,
    CountryProfileRequest,
    CountryProfileView,
    LanguageList,
    LanguageListRequest,
    ParsePhoneNumberRequest,
    PlanQuoteList,
    PlanQuoteRequest,
)
from app.schemas.dto.localization import PhoneNumberDetails
from app.use_cases.catalog.get_country_profile_use_case import GetCountryProfileUseCase
from app.use_cases.catalog.list_countries_use_case import ListCountriesUseCase
from app.use_cases.catalog.list_languages_use_case import ListLanguagesUseCase
from app.use_cases.catalog.quote_plans_use_case import QuotePlansUseCase
from app.use_cases.localization.build_call_forwarding_instructions_use_case import (
    BuildCallForwardingInstructionsUseCase,
)
from app.use_cases.localization.parse_phone_number_use_case import (
    ParsePhoneNumberUseCase,
)


class CatalogUseCasesContainer(containers.DeclarativeContainer):
    """
    The public catalog: countries, languages, plan quotes, phone numbers and
    call forwarding instructions.
    """

    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    parse_phone_number_use_case: Factory[
        UseCaseContract[ParsePhoneNumberRequest, PhoneNumberDetails]
    ] = Factory(
        ParsePhoneNumberUseCase,
        phone_number_parser=utilities.phone_number_parser,
    )
    list_countries_use_case: Factory[
        UseCaseContract[CountryListRequest, CountryList]
    ] = Factory(
        ListCountriesUseCase,
        country_registry=registries.country_registry,
    )
    get_country_profile_use_case: Factory[
        UseCaseContract[CountryProfileRequest, CountryProfileView]
    ] = Factory(
        GetCountryProfileUseCase,
        country_registry=registries.country_registry,
        language_registry=registries.language_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_languages_use_case: Factory[
        UseCaseContract[LanguageListRequest, LanguageList]
    ] = Factory(
        ListLanguagesUseCase,
        language_registry=registries.language_registry,
    )
    quote_plans_use_case: Factory[UseCaseContract[PlanQuoteRequest, PlanQuoteList]] = (
        Factory(
            QuotePlansUseCase,
            plan_registry=registries.plan_registry,
            country_registry=registries.country_registry,
            exchange_rate_registry=registries.exchange_rate_registry,
            localized_text_resolver=utilities.localized_text_resolver,
        )
    )
    build_call_forwarding_instructions_use_case: Factory[
        UseCaseContract[CallForwardingInstructionsQuery, CallForwardingInstructions]
    ] = Factory(
        BuildCallForwardingInstructionsUseCase,
        channel_repo=repositories.channel_repo,
        phone_number_parser=utilities.phone_number_parser,
        call_forwarding_guide_registry=registries.call_forwarding_guide_registry,
        localized_text_resolver=utilities.localized_text_resolver,
    )
