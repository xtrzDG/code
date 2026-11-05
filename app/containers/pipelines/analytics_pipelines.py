from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.analytics_orchestrators import (
    AnalyticsOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class AnalyticsPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the growth analytics."""

    analytics: AnalyticsOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    get_admin_metrics_pipeline = orchestrator_pipeline(
        analytics.get_admin_metrics_orchestrator
    )
    record_telemetry_pipeline = orchestrator_pipeline(
        analytics.record_telemetry_orchestrator
    )
    purge_web_vitals_pipeline = orchestrator_pipeline(
        analytics.purge_web_vitals_orchestrator
    )
    reconcile_product_events_pipeline = orchestrator_pipeline(
        analytics.reconcile_product_events_orchestrator
    )
