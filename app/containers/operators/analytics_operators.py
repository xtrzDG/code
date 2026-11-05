from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.analytics_pipelines import AnalyticsPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class AnalyticsOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the growth analytics: the admin metrics and the daily
    reconciliation read every business (platform-wide); the cabinet's
    telemetry and the Web Vitals purge touch only platform collections.
    """

    analytics_pipelines: AnalyticsPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    get_admin_metrics_operator = platform_pipeline_operator(
        analytics_pipelines.get_admin_metrics_pipeline, storage_scope
    )
    record_telemetry_operator = pipeline_operator(
        analytics_pipelines.record_telemetry_pipeline, storage_scope
    )
    purge_web_vitals_operator = pipeline_operator(
        analytics_pipelines.purge_web_vitals_pipeline, storage_scope
    )
    reconcile_product_events_operator = platform_pipeline_operator(
        analytics_pipelines.reconcile_product_events_pipeline, storage_scope
    )
