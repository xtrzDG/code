from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.telemetry_pipelines import TelemetryPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class TelemetryOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform's metrics, service levels and budgets: those
    that count across every business run platform-wide.
    """

    telemetry_pipelines: TelemetryPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    # Read at every metrics scrape (the API's /metrics, the worker's port).
    measure_job_queues_operator = platform_pipeline_operator(
        telemetry_pipelines.measure_job_queues_pipeline, storage_scope
    )
    # The `record_sli` job reads the inbox and the replies of every business.
    record_service_levels_operator = platform_pipeline_operator(
        telemetry_pipelines.record_service_levels_pipeline, storage_scope
    )
    # These two touch the platform's own SLI collections only.
    add_api_request_counts_operator = pipeline_operator(
        telemetry_pipelines.add_api_request_counts_pipeline, storage_scope
    )
    get_error_budget_operator = pipeline_operator(
        telemetry_pipelines.get_error_budget_pipeline, storage_scope
    )
