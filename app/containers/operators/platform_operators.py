from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.platform_pipelines import PlatformPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class PlatformOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of the platform admin's client views and the LLM trace
    flush job.
    """

    platform_pipelines: PlatformPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Platform admin.
    list_clients_operator = pipeline_operator(
        platform_pipelines.list_clients_pipeline, storage_scope
    )
    get_client_health_operator = pipeline_operator(
        platform_pipelines.get_client_health_pipeline, storage_scope
    )
    open_client_cabinet_operator = pipeline_operator(
        platform_pipelines.open_client_cabinet_pipeline, storage_scope
    )

    # --- Periodic job of the background worker.
    flush_llm_traces_operator = pipeline_operator(
        platform_pipelines.flush_llm_traces_pipeline, storage_scope
    )
    purge_stale_rows_operator = pipeline_operator(
        platform_pipelines.purge_stale_rows_pipeline, storage_scope
    )

    # --- The job queue: the admin's dead letters and the purge job.
    list_queued_jobs_operator = pipeline_operator(
        platform_pipelines.list_queued_jobs_pipeline, storage_scope
    )
    retry_queued_job_operator = pipeline_operator(
        platform_pipelines.retry_queued_job_pipeline, storage_scope
    )
    discard_queued_job_operator = pipeline_operator(
        platform_pipelines.discard_queued_job_pipeline, storage_scope
    )
    purge_finished_jobs_operator = pipeline_operator(
        platform_pipelines.purge_finished_jobs_pipeline, storage_scope
    )
