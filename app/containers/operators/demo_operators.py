from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.demo_pipelines import DemoPipelinesContainer
from app.containers.provider_chains import platform_pipeline_operator
from app.containers.utilities import UtilitiesContainer


class DemoOperatorsContainer(containers.DeclarativeContainer):
    """Operator of the development demo data (SEED_DEMO_DATA, API startup)."""

    demo_pipelines: DemoPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve;
    # platform_pipeline_operator marks platform-level work (platform-wide).
    storage_scope = utilities.storage_scope

    seed_demo_data_operator = platform_pipeline_operator(
        demo_pipelines.seed_demo_data_pipeline, storage_scope
    )
