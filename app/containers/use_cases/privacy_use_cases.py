from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.privacy import BusinessExportLinkSignerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.dto.privacy.business_exports import (
    BusinessExportDownload,
    BusinessExportDownloadQuery,
    BusinessExportList,
    BusinessExportListQuery,
    BusinessExportView,
    StartBusinessExportCommand,
)
from app.schemas.dto.privacy.csv_exports import (
    CsvExportHeader,
    CsvExportPage,
    CsvExportPageQuery,
    StartCsvExportCommand,
)
from app.use_cases.exports.business_archive import BusinessArchiveBuilder
from app.use_cases.exports.download_business_export_use_case import (
    DownloadBusinessExportUseCase,
)
from app.use_cases.exports.list_business_exports_use_case import (
    ListBusinessExportsUseCase,
)
from app.use_cases.exports.purge_business_exports_use_case import (
    PurgeBusinessExportsUseCase,
)
from app.use_cases.exports.read_csv_export_page_use_case import (
    ReadCsvExportPageUseCase,
)
from app.use_cases.exports.run_business_export_use_case import (
    RunBusinessExportUseCase,
)
from app.use_cases.exports.start_business_export_use_case import (
    StartBusinessExportUseCase,
)
from app.use_cases.exports.start_csv_export_use_case import StartCsvExportUseCase
from app.utilities.privacy.export_link_signer import BusinessExportLinkSigner


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

    # --- The full export: a ZIP the worker writes, a signed link for a day.
    export_link_signer: Singleton[BusinessExportLinkSignerContract] = Singleton(
        BusinessExportLinkSigner,
        encryption_key=config.app_settings.provided.encryption_key,
        previous_keys=config.app_settings.provided.previous_encryption_keys,
    )
    business_archive_builder: Factory[BusinessArchiveBuilder] = Factory(
        BusinessArchiveBuilder,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        call_repo=repositories.call_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        missed_call_repo=repositories.missed_call_repo,
        feedback_request_repo=repositories.feedback_request_repo,
        audit_log_repo=repositories.audit_log_repo,
        text_resolver=utilities.localized_text_resolver,
    )
    start_business_export_use_case: Factory[
        UseCaseContract[StartBusinessExportCommand, BusinessExportView]
    ] = Factory(
        StartBusinessExportUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        export_repo=repositories.business_export_repo,
        job_queue=facilitators.job_queue_facilitator,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        step_up=utilities.step_up_guard,
        link_signer=export_link_signer,
    )
    list_business_exports_use_case: Factory[
        UseCaseContract[BusinessExportListQuery, BusinessExportList]
    ] = Factory(
        ListBusinessExportsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        export_repo=repositories.business_export_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        link_signer=export_link_signer,
    )
    run_business_export_use_case: Factory[
        UseCaseContract[QueuedJobInput, JobReport]
    ] = Factory(
        RunBusinessExportUseCase,
        business_repo=repositories.business_repo,
        export_repo=repositories.business_export_repo,
        archive_builder=business_archive_builder,
        archive_storage=adapters.export_archive_storage,
        wall_clock=time_provider.microsecond_wall_clock,
        link_hours=config.app_settings.provided.privacy.provided.export_link_hours,
    )
    download_business_export_use_case: Factory[
        UseCaseContract[BusinessExportDownloadQuery, BusinessExportDownload]
    ] = Factory(
        DownloadBusinessExportUseCase,
        business_repo=repositories.business_repo,
        export_repo=repositories.business_export_repo,
        archive_storage=adapters.export_archive_storage,
        link_signer=export_link_signer,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    purge_business_exports_use_case: Factory[UseCaseContract[JobTick, JobReport]] = (
        Factory(
            PurgeBusinessExportsUseCase,
            export_repo=repositories.business_export_repo,
            archive_storage=adapters.export_archive_storage,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
