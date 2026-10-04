from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.privacy.csv_exports import (
    CsvExportHeader,
    CsvExportPage,
    CsvExportPageQuery,
    StartCsvExportCommand,
)
from app.use_cases.exports.read_csv_export_page_use_case import (
    ReadCsvExportPageUseCase,
)
from app.use_cases.exports.start_csv_export_use_case import StartCsvExportUseCase


class PrivacyUseCasesContainer(containers.DeclarativeContainer):
    """
    Exports of a business's data: the cabinet's tables as streamed CSV and
    the full export of every collection.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    start_csv_export_use_case: Factory[
        UseCaseContract[StartCsvExportCommand, CsvExportHeader]
    ] = Factory(
        StartCsvExportUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
        text_resolver=utilities.localized_text_resolver,
    )
    read_csv_export_page_use_case: Factory[
        UseCaseContract[CsvExportPageQuery, CsvExportPage]
    ] = Factory(
        ReadCsvExportPageUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        booking_repo=repositories.booking_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        lead_repo=repositories.lead_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        audit_log_repo=repositories.audit_log_repo,
        phone_number_parser=utilities.phone_number_parser,
    )
