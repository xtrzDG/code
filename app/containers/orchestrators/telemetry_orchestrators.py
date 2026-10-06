from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.telemetry_use_cases import TelemetryUseCasesContainer


class TelemetryOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the platform's metrics, service levels and budgets."""

    telemetry_use_cases: TelemetryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    measure_job_queues_orchestrator = use_case_orchestrator(
        telemetry_use_cases.measure_job_queues_use_case
    )
