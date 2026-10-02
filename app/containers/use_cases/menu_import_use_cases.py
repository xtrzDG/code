from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.menu_import import (
    ConfirmImportedItemsCommand,
    ConfirmImportedItemsResult,
    DiscardedImportBatch,
    DiscardImportBatchCommand,
    ImportMenuCommand,
    MenuImportResult,
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
    Menu import: items read from a photo or file, then confirmed into the
    knowledge base or discarded.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
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
