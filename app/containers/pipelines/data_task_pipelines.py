from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.data_task_orchestrators import (
    DataTaskOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class DataTaskPipelinesContainer(containers.DeclarativeContainer):
    """Pipelines of the post-deploy data tasks."""

    data_tasks: DataTaskOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    run_data_tasks_pipeline = orchestrator_pipeline(
        data_tasks.run_data_tasks_orchestrator
    )
    get_data_tasks_pipeline = orchestrator_pipeline(
        data_tasks.get_data_tasks_orchestrator
    )
    retry_data_task_pipeline = orchestrator_pipeline(
        data_tasks.retry_data_task_orchestrator
    )
