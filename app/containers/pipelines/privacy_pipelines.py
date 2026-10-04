from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.privacy_orchestrators import (
    PrivacyOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PrivacyPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the exports of a business's data."""

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
    purge_business_exports_pipeline = orchestrator_pipeline(
        privacy_orchestrators.purge_business_exports_orchestrator
    )
