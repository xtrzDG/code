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
    add_api_request_counts_orchestrator = use_case_orchestrator(
        telemetry_use_cases.add_api_request_counts_use_case
    )
    record_service_levels_orchestrator = use_case_orchestrator(
        telemetry_use_cases.record_service_levels_use_case
    )
    get_error_budget_orchestrator = use_case_orchestrator(
        telemetry_use_cases.get_error_budget_use_case
    )
