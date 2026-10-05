from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.privacy_use_cases import PrivacyUseCasesContainer


class PrivacyOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the exports and the retention of a business's data."""

    privacy_use_cases: PrivacyUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    start_csv_export_orchestrator = use_case_orchestrator(
        privacy_use_cases.start_csv_export_use_case
    )
    read_csv_export_page_orchestrator = use_case_orchestrator(
        privacy_use_cases.read_csv_export_page_use_case
    )
    start_business_export_orchestrator = use_case_orchestrator(
        privacy_use_cases.start_business_export_use_case
    )
    list_business_exports_orchestrator = use_case_orchestrator(
        privacy_use_cases.list_business_exports_use_case
    )
    run_business_export_orchestrator = use_case_orchestrator(
        privacy_use_cases.run_business_export_use_case
    )
    download_business_export_orchestrator = use_case_orchestrator(
        privacy_use_cases.download_business_export_use_case
    )
    purge_business_exports_orchestrator = use_case_orchestrator(
        privacy_use_cases.purge_business_exports_use_case
    )
    get_privacy_settings_orchestrator = use_case_orchestrator(
        privacy_use_cases.get_privacy_settings_use_case
    )
    update_privacy_settings_orchestrator = use_case_orchestrator(
        privacy_use_cases.update_privacy_settings_use_case
    )
    purge_expired_personal_data_orchestrator = use_case_orchestrator(
        privacy_use_cases.purge_expired_personal_data_use_case
    )
    erase_processor_copies_orchestrator = use_case_orchestrator(
        privacy_use_cases.erase_processor_copies_use_case
    )
