from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.telemetry_orchestrators import (
    TelemetryOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class TelemetryPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the platform's metrics, service levels and budgets."""

    telemetry_orchestrators: TelemetryOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    measure_job_queues_pipeline = orchestrator_pipeline(
        telemetry_orchestrators.measure_job_queues_orchestrator
    )
    add_api_request_counts_pipeline = orchestrator_pipeline(
        telemetry_orchestrators.add_api_request_counts_orchestrator
    )
    record_service_levels_pipeline = orchestrator_pipeline(
        telemetry_orchestrators.record_service_levels_orchestrator
    )
    get_error_budget_pipeline = orchestrator_pipeline(
        telemetry_orchestrators.get_error_budget_orchestrator
    )
