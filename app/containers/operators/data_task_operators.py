from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.data_task_pipelines import DataTaskPipelinesContainer
from app.containers.provider_chains import platform_pipeline_operator
from app.containers.utilities import UtilitiesContainer


class DataTaskOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the post-deploy data tasks: they walk and report tables of
    every business, so all three run platform-wide.
    """

    data_task_pipelines: DataTaskPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    storage_scope = utilities.storage_scope

    run_data_tasks_operator = platform_pipeline_operator(
        data_task_pipelines.run_data_tasks_pipeline, storage_scope
    )
    get_data_tasks_operator = platform_pipeline_operator(
        data_task_pipelines.get_data_tasks_pipeline, storage_scope
    )
    retry_data_task_operator = platform_pipeline_operator(
        data_task_pipelines.retry_data_task_pipeline, storage_scope
    )
