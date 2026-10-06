from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.reliability_orchestrators import (
    ReliabilityOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class ReliabilityPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the platform's reliability seen from the API."""

    reliability: ReliabilityOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    check_pipeline_health_pipeline = orchestrator_pipeline(
        reliability.check_pipeline_health_orchestrator
    )
    watch_pipeline_pipeline = orchestrator_pipeline(
        reliability.watch_pipeline_orchestrator
    )
