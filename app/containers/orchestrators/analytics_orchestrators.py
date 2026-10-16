from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.analytics_use_cases import AnalyticsUseCasesContainer


class AnalyticsOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the growth analytics (one use case each)."""

    analytics_use_cases: AnalyticsUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    get_admin_metrics_orchestrator = use_case_orchestrator(
        analytics_use_cases.get_admin_metrics_use_case
    )
    record_telemetry_orchestrator = use_case_orchestrator(
        analytics_use_cases.record_telemetry_use_case
    )
    purge_web_vitals_orchestrator = use_case_orchestrator(
        analytics_use_cases.purge_web_vitals_use_case
    )
    reconcile_product_events_orchestrator = use_case_orchestrator(
        analytics_use_cases.reconcile_product_events_use_case
    )
