from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.assistant_pipelines import AssistantPipelinesContainer
from app.containers.provider_chains import pipeline_operator
from app.containers.utilities import UtilitiesContainer


class AssistantOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of assistant versions: assembly, autotests, go-live
    readiness, publishing and rollback.
    """

    assistant_pipelines: AssistantPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve.
    storage_scope = utilities.storage_scope

    # --- Dedicated pipelines and orchestrators.
    assemble_assistant_version_operator = pipeline_operator(
        assistant_pipelines.assemble_assistant_version_pipeline, storage_scope
    )
    run_autotests_operator = pipeline_operator(
        assistant_pipelines.run_autotests_pipeline, storage_scope
    )
    run_queued_autotests_operator = pipeline_operator(
        assistant_pipelines.run_queued_autotests_pipeline, storage_scope
    )
    apply_changes_operator = pipeline_operator(
        assistant_pipelines.apply_changes_pipeline, storage_scope
    )
    get_apply_changes_operator = pipeline_operator(
        assistant_pipelines.get_apply_changes_pipeline, storage_scope
    )
    get_pending_changes_operator = pipeline_operator(
        assistant_pipelines.get_pending_changes_pipeline, storage_scope
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_operator = pipeline_operator(
        assistant_pipelines.list_assistant_versions_pipeline, storage_scope
    )
    get_assistant_version_operator = pipeline_operator(
        assistant_pipelines.get_assistant_version_pipeline, storage_scope
    )
    get_autotest_run_operator = pipeline_operator(
        assistant_pipelines.get_autotest_run_pipeline, storage_scope
    )
    list_autotest_cases_operator = pipeline_operator(
        assistant_pipelines.list_autotest_cases_pipeline, storage_scope
    )
    create_autotest_case_operator = pipeline_operator(
        assistant_pipelines.create_autotest_case_pipeline, storage_scope
    )
    update_autotest_case_operator = pipeline_operator(
        assistant_pipelines.update_autotest_case_pipeline, storage_scope
    )
    delete_autotest_case_operator = pipeline_operator(
        assistant_pipelines.delete_autotest_case_pipeline, storage_scope
    )
    get_go_live_readiness_operator = pipeline_operator(
        assistant_pipelines.get_go_live_readiness_pipeline, storage_scope
    )
    publish_assistant_version_operator = pipeline_operator(
        assistant_pipelines.publish_assistant_version_pipeline, storage_scope
    )
    rollback_assistant_version_operator = pipeline_operator(
        assistant_pipelines.rollback_assistant_version_pipeline, storage_scope
    )
