from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.demo.demo_dataset_registry import DemoDatasetRegistry
from app.registries.legal.legal_document_registry import LegalDocumentRegistry
from app.registries.limits.request_rate_limit_registry import (
    RequestRateLimitRegistry,
)
from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.registries.localization.country_registry import CountryRegistry
from app.registries.localization.high_cost_phone_number_registry import (
    HighCostPhoneNumberRegistry,
)
from app.registries.localization.language_registry import LanguageRegistry
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.registries.locks.customer_message_lock_registry import (
    CustomerMessageLockRegistry,
)
from app.registries.locks.login_code_send_lock_registry import (
    LoginCodeSendLockRegistry,
)
from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.registries.tools.assistant_tool_registry import AssistantToolRegistry


class RegistriesContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
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
    # Data processing agreement texts (docs/legal), read once per process.
    legal_document_registry: Singleton[LegalDocumentRegistry] = Singleton(
        LegalDocumentRegistry
    )
    # Locks every API instance and worker respects (Postgres advisory locks;
    # in-process locks without a database): one per business around booking
    # writes, one per customer around a turn, one for login code sends.
    business_lock_registry: Singleton[BusinessLockRegistry] = Singleton(
        BusinessLockRegistry, advisory_locks=adapters.advisory_locks
    )
    customer_message_lock_registry: Singleton[CustomerMessageLockRegistry] = Singleton(
        CustomerMessageLockRegistry, advisory_locks=adapters.advisory_locks
    )
    # Request counters of public endpoints (the website widget, login code
    # checks), shared by every API instance through Postgres.
    request_rate_limit_registry: Singleton[RequestRateLimitRegistry] = Singleton(
        RequestRateLimitRegistry, buckets=adapters.rate_limit_buckets
    )
    # One lock for reserving login code sends (the hourly limits).
    login_code_send_lock_registry: Singleton[LoginCodeSendLockRegistry] = Singleton(
        LoginCodeSendLockRegistry, advisory_locks=adapters.advisory_locks
    )
    # Numbers a login code is never sent to (premium rate, satellite, ...).
    high_cost_phone_number_registry: Singleton[HighCostPhoneNumberRegistry] = Singleton(
        HighCostPhoneNumberRegistry,
        denied_prefixes=config.app_settings.provided.otp_denied_phone_prefixes,
    )
    # Development demo businesses (SEED_DEMO_DATA), built for the moment of
    # seeding.
    demo_dataset_registry: Singleton[DemoDatasetRegistry] = Singleton(
        DemoDatasetRegistry, plan_registry=plan_registry
    )
