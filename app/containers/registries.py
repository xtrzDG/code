from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.registries.access.platform_admin_registry import PlatformAdminRegistry
from app.registries.billing.exchange_rate_registry import ExchangeRateRegistry
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.demo.demo_dataset_registry import DemoDatasetRegistry
from app.registries.demo.load_dataset_registry import LoadDatasetRegistry
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
from app.registries.niches.niche_value_registry import NicheValueRegistry
from app.registries.niches.starter_answer_registry import StarterAnswerRegistry
from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.registries.turns.turn_slot_registry import (
    TurnSlotRegistry,
    build_customer_turn_slots,
    build_test_chat_slots,
)


class RegistriesContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    language_registry: Singleton[LanguageRegistry] = Singleton(LanguageRegistry)
    # Platform admin roles from the admin team, read at every check; the
    # PLATFORM_ADMIN_* lists only bootstrap the first SUPER admin (1103).
    platform_admin_registry: Singleton[PlatformAdminRegistry] = Singleton(
        PlatformAdminRegistry,
        platform_admin_repo=repositories.platform_admin_repo,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
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
    starter_answer_registry: Singleton[StarterAnswerRegistry] = Singleton(
        StarterAnswerRegistry
    )
    # What a booking of each niche typically brings and the staff time a
    # reply or a call takes (the value estimates).
    niche_value_registry: Singleton[NicheValueRegistry] = Singleton(NicheValueRegistry)
    plan_registry: Singleton[PlanRegistry] = Singleton(PlanRegistry)
    # Dated rates of the NBG and ECB feeds, the catalog as fallback.
    exchange_rate_registry: Singleton[ExchangeRateRegistry] = Singleton(
        ExchangeRateRegistry,
        exchange_rate_repo=repositories.exchange_rate_repo,
        wall_clock=time_provider.microsecond_wall_clock,
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
    # Places for turns in this process, taken before anything held for long:
    # customer turns before their lock (LLM_MAX_CONCURRENCY), the owners'
    # test chat before its model calls (TEST_CHAT_MAX_CONCURRENCY).
    customer_turn_slots: Singleton[TurnSlotRegistry] = Singleton(
        build_customer_turn_slots, settings=config.app_settings
    )
    test_chat_slots: Singleton[TurnSlotRegistry] = Singleton(
        build_test_chat_slots, settings=config.app_settings
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
    # Bulk histories of load-test businesses (`workshop seed-load`).
    load_dataset_registry: Singleton[LoadDatasetRegistry] = Singleton(
        LoadDatasetRegistry
    )
