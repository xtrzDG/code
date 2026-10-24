from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.legal_use_cases import LegalUseCasesContainer


class LegalOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the legal texts, the sub-processor list and its notices."""

    legal_use_cases: LegalUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_subprocessors_orchestrator = use_case_orchestrator(
        legal_use_cases.get_subprocessors_use_case
    )
    get_legal_document_orchestrator = use_case_orchestrator(
        legal_use_cases.get_legal_document_use_case
    )
    get_legal_overview_orchestrator = use_case_orchestrator(
        legal_use_cases.get_legal_overview_use_case
    )
    send_subprocessor_notices_orchestrator = use_case_orchestrator(
        legal_use_cases.send_subprocessor_notices_use_case
    )
