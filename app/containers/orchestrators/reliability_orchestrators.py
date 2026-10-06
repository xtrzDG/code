from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.reliability_use_cases import (
    ReliabilityUseCasesContainer,
)


class ReliabilityOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the platform's reliability seen from the API."""

    reliability_use_cases: ReliabilityUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    check_pipeline_health_orchestrator = use_case_orchestrator(
        reliability_use_cases.check_pipeline_health_use_case
    )
    watch_pipeline_orchestrator = use_case_orchestrator(
        reliability_use_cases.watch_pipeline_use_case
    )
