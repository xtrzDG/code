from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.privacy_orchestrators import (
    PrivacyOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PrivacyPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the exports and the retention of a business's data."""

    privacy_orchestrators: PrivacyOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    start_csv_export_pipeline = orchestrator_pipeline(
        privacy_orchestrators.start_csv_export_orchestrator
    )
    read_csv_export_page_pipeline = orchestrator_pipeline(
        privacy_orchestrators.read_csv_export_page_orchestrator
    )
    start_business_export_pipeline = orchestrator_pipeline(
        privacy_orchestrators.start_business_export_orchestrator
    )
    list_business_exports_pipeline = orchestrator_pipeline(
        privacy_orchestrators.list_business_exports_orchestrator
    )
    run_business_export_pipeline = orchestrator_pipeline(
        privacy_orchestrators.run_business_export_orchestrator
    )
    download_business_export_pipeline = orchestrator_pipeline(
        privacy_orchestrators.download_business_export_orchestrator
    )
    create_export_download_link_pipeline = orchestrator_pipeline(
        privacy_orchestrators.create_export_download_link_orchestrator
    )
    purge_business_exports_pipeline = orchestrator_pipeline(
        privacy_orchestrators.purge_business_exports_orchestrator
    )
    get_privacy_settings_pipeline = orchestrator_pipeline(
        privacy_orchestrators.get_privacy_settings_orchestrator
    )
    update_privacy_settings_pipeline = orchestrator_pipeline(
        privacy_orchestrators.update_privacy_settings_orchestrator
    )
    purge_expired_personal_data_pipeline = orchestrator_pipeline(
        privacy_orchestrators.purge_expired_personal_data_orchestrator
    )
    erase_processor_copies_pipeline = orchestrator_pipeline(
        privacy_orchestrators.erase_processor_copies_orchestrator
    )
