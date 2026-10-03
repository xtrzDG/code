from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.demo_orchestrators import DemoOrchestratorsContainer
from app.containers.provider_chains import orchestrator_pipeline


class DemoPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the development demo data (SEED_DEMO_DATA, API startup) and
    of load-test datasets (`workshop seed-load`).
    """

    demo_orchestrators: DemoOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    seed_demo_data_pipeline = orchestrator_pipeline(
        demo_orchestrators.seed_demo_data_orchestrator
    )
    seed_load_pipeline = orchestrator_pipeline(
        demo_orchestrators.seed_load_orchestrator
    )
