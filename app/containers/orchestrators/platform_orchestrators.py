from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer


class PlatformOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of the platform admin's client views and the LLM trace
    flush job.
    """

    platform_use_cases: PlatformUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Platform admin.
    list_clients_orchestrator = use_case_orchestrator(
        platform_use_cases.list_clients_use_case
    )
    get_client_health_orchestrator = use_case_orchestrator(
        platform_use_cases.get_client_health_use_case
    )
    open_client_cabinet_orchestrator = use_case_orchestrator(
        platform_use_cases.open_client_cabinet_use_case
    )

    # --- Periodic job of the background worker.
    flush_llm_traces_orchestrator = use_case_orchestrator(
        platform_use_cases.flush_llm_traces_use_case
    )
    purge_stale_rows_orchestrator = use_case_orchestrator(
        platform_use_cases.purge_stale_rows_use_case
    )
