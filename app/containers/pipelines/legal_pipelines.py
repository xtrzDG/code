from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.legal_orchestrators import (
    LegalOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class LegalPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the legal texts, the sub-processor list and its notices."""

    legal_orchestrators: LegalOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_subprocessors_pipeline = orchestrator_pipeline(
        legal_orchestrators.get_subprocessors_orchestrator
    )
    get_legal_document_pipeline = orchestrator_pipeline(
        legal_orchestrators.get_legal_document_orchestrator
    )
    send_subprocessor_notices_pipeline = orchestrator_pipeline(
        legal_orchestrators.send_subprocessor_notices_orchestrator
    )
