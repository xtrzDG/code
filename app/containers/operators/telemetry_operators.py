from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.telemetry_pipelines import TelemetryPipelinesContainer
from app.containers.provider_chains import platform_pipeline_operator
from app.containers.utilities import UtilitiesContainer


class TelemetryOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform's metrics, service levels and budgets; all
    platform-wide (they count across every business).
    """

    telemetry_pipelines: TelemetryPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    # Read at every metrics scrape (the API's /metrics, the worker's port).
    measure_job_queues_operator = platform_pipeline_operator(
        telemetry_pipelines.measure_job_queues_pipeline, storage_scope
    )
