from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.adapters.llm.website_extraction.website_extraction_adapter import (
    WebsiteExtractionAdapter,
)
from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.website_import import WebsiteExtractionAdapterContract
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportResult,
)
from app.schemas.dto.website_import import (
    CurrentWebsiteImport,
    GetWebsiteImportQuery,
    StartWebsiteImportCommand,
    WebsiteImportView,
)
from app.use_cases.knowledge.website_import.get_website_import_use_case import (
    GetWebsiteImportUseCase,
)
from app.use_cases.knowledge.website_import.run_website_import_use_case import (
    RunWebsiteImportUseCase,
)
from app.use_cases.knowledge.website_import.start_website_import_use_case import (
    StartWebsiteImportUseCase,
)
from app.use_cases.menu_import.confirm_imported_items_use_case import (
    ConfirmImportedItemsUseCase,
)
from app.use_cases.menu_import.discard_import_batch_use_case import (
    DiscardImportBatchUseCase,
)
from app.use_cases.menu_import.import_menu_use_case import ImportMenuUseCase


class MenuImportUseCasesContainer(containers.DeclarativeContainer):
    """
    Knowledge imports: items read from a menu photo, file or link, or from
    the business's website (a queued job), then confirmed into the
    knowledge base or discarded.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    import_menu_use_case: Factory[
        UseCaseContract[ImportMenuCommand, MenuImportResult]
    ] = Factory(
        ImportMenuUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        menu_extraction_adapter=adapters.menu_extraction_adapter,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    confirm_imported_items_use_case: Factory[
        UseCaseContract[ConfirmImportedItemsCommand, ConfirmImportedItemsResult]
    ] = Factory(
        ConfirmImportedItemsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        knowledge_item_repo=repositories.knowledge_item_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    discard_import_batch_use_case: Factory[
        UseCaseContract[DiscardImportBatchCommand, DiscardedImportBatch]
    ] = Factory(
        DiscardImportBatchUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )

    # --- Website import. The reader asks the assistants' model (the
    # routed, traced, concurrency-limited adapter) about one page at a time.
    website_extraction_adapter: Singleton[WebsiteExtractionAdapterContract] = Singleton(
        WebsiteExtractionAdapter,
        llm_adapter=adapters.llm_adapter,
        model_id=config.app_settings.provided.llm_model_id,
    )
    start_website_import_use_case: Factory[
        UseCaseContract[StartWebsiteImportCommand, WebsiteImportView]
    ] = Factory(
        StartWebsiteImportUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        safe_http_fetcher=clients.safe_http_fetcher,
        website_import_repo=repositories.website_import_repo,
        rate_limit_registry=registries.request_rate_limit_registry,
        job_queue=facilitators.job_queue_facilitator,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_website_import_use_case: Factory[
        UseCaseContract[GetWebsiteImportQuery, CurrentWebsiteImport]
    ] = Factory(
        GetWebsiteImportUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        website_import_repo=repositories.website_import_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
    )
    # The worker's job (IMPORT_WEBSITE_JOB).
    run_website_import_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]] = (
        Factory(
            RunWebsiteImportUseCase,
            website_import_repo=repositories.website_import_repo,
            business_repo=repositories.business_repo,
            niche_template_registry=registries.niche_template_registry,
            knowledge_item_repo=repositories.knowledge_item_repo,
            usage_event_repo=repositories.usage_event_repo,
            safe_http_fetcher=clients.safe_http_fetcher,
            website_extraction_adapter=website_extraction_adapter,
            live_events=facilitators.event_publisher,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
