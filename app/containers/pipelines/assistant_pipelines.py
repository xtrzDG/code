from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.orchestrators.assistant_orchestrators import (
    AssistantOrchestratorsContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.contracts.pipeline_contract import PipelineContract
from app.pipelines.assistants.assemble_assistant_version_pipeline import (
    AssembleAssistantVersionPipeline,
)
from app.schemas.dto.assistants.assistant_commands import (
    AssembleAssistantVersionCommand,
)
from app.schemas.dto.assistants.assistant_views import AssistantVersionDetails


class AssistantPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of assistant versions: assembly, autotests, go-live
    readiness, publishing and rollback.
    """

    assistant_orchestrators: AssistantOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Assembly then autotests; autotest runs played by the worker.
    assemble_assistant_version_pipeline: Factory[
        PipelineContract[AssembleAssistantVersionCommand, AssistantVersionDetails]
    ] = Factory(
        AssembleAssistantVersionPipeline,
        assemble_assistant_version=assistant_orchestrators.assemble_assistant_version_orchestrator,
        run_autotests=assistant_orchestrators.queue_autotest_run_orchestrator,
        get_assistant_version=assistant_orchestrators.get_assistant_version_orchestrator,
    )
    run_autotests_pipeline = orchestrator_pipeline(
        assistant_orchestrators.queue_autotest_run_orchestrator
    )
    run_queued_autotests_pipeline = orchestrator_pipeline(
        assistant_orchestrators.run_queued_autotests_orchestrator
    )
    apply_changes_pipeline = orchestrator_pipeline(
        assistant_orchestrators.apply_changes_orchestrator
    )
    get_apply_changes_pipeline = orchestrator_pipeline(
        assistant_orchestrators.get_apply_changes_orchestrator
    )

    # --- Assistant versions and autotests.
    list_assistant_versions_pipeline = orchestrator_pipeline(
        assistant_orchestrators.list_assistant_versions_orchestrator
    )
    get_assistant_version_pipeline = orchestrator_pipeline(
        assistant_orchestrators.get_assistant_version_orchestrator
    )
    get_autotest_run_pipeline = orchestrator_pipeline(
        assistant_orchestrators.get_autotest_run_orchestrator
    )
    get_go_live_readiness_pipeline = orchestrator_pipeline(
        assistant_orchestrators.get_go_live_readiness_orchestrator
    )
    publish_assistant_version_pipeline = orchestrator_pipeline(
        assistant_orchestrators.publish_assistant_version_orchestrator
    )
    rollback_assistant_version_pipeline = orchestrator_pipeline(
        assistant_orchestrators.rollback_assistant_version_orchestrator
    )
