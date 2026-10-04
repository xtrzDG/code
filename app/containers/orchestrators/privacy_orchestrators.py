from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.privacy_use_cases import PrivacyUseCasesContainer


class PrivacyOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the exports of a business's data."""

    privacy_use_cases: PrivacyUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    start_csv_export_orchestrator = use_case_orchestrator(
        privacy_use_cases.start_csv_export_use_case
    )
    read_csv_export_page_orchestrator = use_case_orchestrator(
        privacy_use_cases.read_csv_export_page_use_case
    )
