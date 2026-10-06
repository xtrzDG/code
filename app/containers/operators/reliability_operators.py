from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.reliability_pipelines import (
    ReliabilityPipelinesContainer,
)
from app.containers.provider_chains import platform_pipeline_operator
from app.containers.utilities import UtilitiesContainer


class ReliabilityOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform's reliability seen from the API: the
    pipeline check and the watchdog read worker pulses, the job queue and
    the alert states of no single business, so they run platform-wide.
    """

    reliability_pipelines: ReliabilityPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    check_pipeline_health_operator = platform_pipeline_operator(
        reliability_pipelines.check_pipeline_health_pipeline, storage_scope
    )
    watch_pipeline_operator = platform_pipeline_operator(
        reliability_pipelines.watch_pipeline_pipeline, storage_scope
    )
