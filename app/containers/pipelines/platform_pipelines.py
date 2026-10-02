from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.orchestrators.platform_orchestrators import (
    PlatformOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline


class PlatformPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of the platform admin's client views and the LLM trace
    flush job.
    """

    platform_orchestrators: PlatformOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Platform admin.
    list_clients_pipeline = orchestrator_pipeline(
        platform_orchestrators.list_clients_orchestrator
    )
    get_client_health_pipeline = orchestrator_pipeline(
        platform_orchestrators.get_client_health_orchestrator
    )
    open_client_cabinet_pipeline = orchestrator_pipeline(
        platform_orchestrators.open_client_cabinet_orchestrator
    )

    # --- Periodic job of the background worker.
    flush_llm_traces_pipeline = orchestrator_pipeline(
        platform_orchestrators.flush_llm_traces_orchestrator
    )
    purge_stale_rows_pipeline = orchestrator_pipeline(
        platform_orchestrators.purge_stale_rows_orchestrator
    )
