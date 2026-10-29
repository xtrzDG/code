from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.data_task_use_cases import DataTaskUseCasesContainer


class DataTaskOrchestratorsContainer(containers.DeclarativeContainer):
    """Orchestrators of the post-deploy data tasks (one use case each)."""

    data_task_use_cases: DataTaskUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    run_data_tasks_orchestrator = use_case_orchestrator(
        data_task_use_cases.run_data_tasks_use_case
    )
    get_data_tasks_orchestrator = use_case_orchestrator(
        data_task_use_cases.get_data_tasks_use_case
    )
    retry_data_task_orchestrator = use_case_orchestrator(
        data_task_use_cases.retry_data_task_use_case
    )
