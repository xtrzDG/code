from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.registries.localization.country_registry import CountryRegistry
from app.registries.localization.language_registry import LanguageRegistry
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.tools.assistant_tool_registry import AssistantToolRegistry


class RegistriesContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    language_registry: Singleton[LanguageRegistry] = Singleton(LanguageRegistry)
    # Profiles of every country are built once (about 0.5 s) and cached; the
    # HTTP application warms them at startup.
    country_registry: Singleton[CountryRegistry] = Singleton(
        CountryRegistry,
        language_registry=language_registry,
        wall_clock=time_provider.microsecond_wall_clock,
        default_data_region=config.app_settings.provided.default_data_region,
        restricted_country_codes=config.app_settings.provided.restricted_country_codes,
    )
    niche_template_registry: Singleton[NicheTemplateRegistry] = Singleton(
        NicheTemplateRegistry
    )
    plan_registry: Singleton[PlanRegistry] = Singleton(PlanRegistry)
    exchange_rate_registry: Singleton[ExchangeRateRegistry] = Singleton(
        ExchangeRateRegistry
    )
    call_forwarding_guide_registry: Singleton[CallForwardingGuideRegistry] = Singleton(
        CallForwardingGuideRegistry
    )
    # Tool definitions of the chat; also the catalog the voice agent is built
    # from (AssistantToolCatalogContract), so both offer the same tools.
    assistant_tool_registry: Singleton[AssistantToolRegistry] = Singleton(
        AssistantToolRegistry
    )
    # One lock per business shared by every booking use case of the process.
    business_lock_registry: Singleton[BusinessLockRegistry] = Singleton(
        BusinessLockRegistry
    )
