from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.demo_data import (
    DemoActivityStorage,
    DemoBusinessFoundation,
    DemoSeedPlan,
    SeedDemoDataCommand,
)
from app.schemas.dto.load_data import (
    LoadBusinessSeed,
    LoadSeedPlan,
    LoadVolumeStorage,
    SeedLoadCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.demo.load.prepare_load_businesses_use_case import (
    PrepareLoadBusinessesUseCase,
)
from app.use_cases.demo.load.store_load_volume_use_case import (
    StoreLoadVolumeUseCase,
)
from app.use_cases.demo.prepare_demo_accounts_use_case import (
    PrepareDemoAccountsUseCase,
)
from app.use_cases.demo.store_demo_activity_use_case import StoreDemoActivityUseCase
from app.use_cases.demo.store_demo_foundation_use_case import (
    StoreDemoFoundationUseCase,
)


class DemoUseCasesContainer(containers.DeclarativeContainer):
    """
    Development demo data (SEED_DEMO_DATA): the demo accounts, the stored
    businesses with their knowledge and channels, and a month of activity;
    and load-test datasets (`workshop seed-load`) built from them.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    prepare_demo_accounts_use_case: Factory[
        UseCaseContract[SeedDemoDataCommand, DemoSeedPlan]
    ] = Factory(
        PrepareDemoAccountsUseCase,
        demo_dataset_registry=registries.demo_dataset_registry,
        user_repo=repositories.user_repo,
        business_repo=repositories.business_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    store_demo_foundation_use_case: Factory[
        UseCaseContract[DemoBusinessFoundation, BusinessId]
    ] = Factory(
        StoreDemoFoundationUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
    )
    store_demo_activity_use_case: Factory[
        UseCaseContract[DemoActivityStorage, BusinessId]
    ] = Factory(
        StoreDemoActivityUseCase,
        demo_dataset_registry=registries.demo_dataset_registry,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        call_repo=repositories.call_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        subscription_repo=repositories.subscription_repo,
        invoice_repo=repositories.invoice_repo,
        usage_event_repo=repositories.usage_event_repo,
        package_usage_warning_repo=repositories.package_usage_warning_repo,
        dpa_acceptance_repo=repositories.dpa_acceptance_repo,
        audit_log_repo=repositories.audit_log_repo,
        review_settings_repo=repositories.review_settings_repo,
        feedback_request_repo=repositories.feedback_request_repo,
        message_media_repo=repositories.message_media_repo,
        media_storage=adapters.media.media_storage,
        conversation_topics_repo=repositories.conversation_topics_repo,
        app_settings=config.app_settings,
    )
    # `workshop seed-load`: owners and plans, then each business's bulk history.
    prepare_load_businesses_use_case: Factory[
        UseCaseContract[SeedLoadCommand, LoadSeedPlan]
    ] = Factory(
        PrepareLoadBusinessesUseCase,
        demo_dataset_registry=registries.demo_dataset_registry,
        user_repo=repositories.user_repo,
        user_session_repo=repositories.user_session_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    store_load_volume_use_case: Factory[
        UseCaseContract[LoadVolumeStorage, LoadBusinessSeed]
    ] = Factory(
        StoreLoadVolumeUseCase,
        load_dataset_registry=registries.load_dataset_registry,
        business_repo=repositories.business_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        booking_repo=repositories.booking_repo,
        app_settings=config.app_settings,
    )
