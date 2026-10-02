from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
)
from app.containers.provider_chains import use_case_orchestrator
from app.containers.repositories import RepositoriesContainer
from app.containers.use_cases.apply_use_cases import ApplyUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.autotest_use_cases import AutotestUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.orchestrators.assistants.apply_changes_orchestrator import (
    ApplyChangesOrchestrator,
)
from app.orchestrators.assistants.queue_autotest_run_orchestrator import (
    QueueAutotestRunOrchestrator,
)
from app.orchestrators.assistants.run_autotests_orchestrator import (
    RunAutotestsOrchestrator,
)
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.setup.apply_changes import ApplyChangesCommand, ApplyChangesView
from app.use_cases.autotests.run_autotest_scenario_use_case import (
    RunAutotestScenarioUseCase,
)


class AssistantOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of assistant versions: assembly, autotests, go-live
    readiness, publishing and rollback.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    assistant_use_cases: AssistantUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    autotest_use_cases: AutotestUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    apply_use_cases: ApplyUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_orchestrators: ConversationOrchestratorsContainer = (
        DependenciesContainer()  # type: ignore[assignment]
    )

    # --- Autotests: AI customer and judge share the traced LLM adapter.
    run_autotest_scenario_use_case: Factory[
        UseCaseContract[AutotestScenarioRun, AutotestScenarioResult]
    ] = Factory(
        RunAutotestScenarioUseCase,
        conversation_turn_orchestrator=conversation_orchestrators.conversation_turn_orchestrator,
        customer_llm_adapter=adapters.llm_adapter,
        judge_llm_adapter=adapters.llm_adapter,
        message_repo=repositories.message_repo,
        app_settings=config.app_settings,
    )
    run_autotests_orchestrator: Factory[
        OrchestratorContract[RunAutotestsCommand, AutotestRunView]
    ] = Factory(
        RunAutotestsOrchestrator,
        start_autotest_run=autotest_use_cases.start_autotest_run_use_case,
        run_autotest_scenario=run_autotest_scenario_use_case,
        finish_autotest_run=autotest_use_cases.finish_autotest_run_use_case,
    )
    # The HTTP routes start a run and leave playing it to the worker.
    queue_autotest_run_orchestrator: Factory[
        OrchestratorContract[RunAutotestsCommand, AutotestRunView]
    ] = Factory(
        QueueAutotestRunOrchestrator,
        start_autotest_run=autotest_use_cases.start_autotest_run_use_case,
        enqueue_autotest_run=autotest_use_cases.enqueue_autotest_run_use_case,
    )
    run_queued_autotests_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        RunQueuedAutotestsOrchestrator,
        resume_autotest_run=autotest_use_cases.resume_autotest_run_use_case,
        run_autotest_scenario=run_autotest_scenario_use_case,
        finish_autotest_run=autotest_use_cases.finish_autotest_run_use_case,
        abandon_autotest_run=autotest_use_cases.abandon_autotest_run_use_case,
        record_autotest_progress=autotest_use_cases.record_autotest_progress_use_case,
        publish_applied_version=apply_use_cases.publish_applied_version_use_case,
    )
    # "Apply changes": build, check in the background, publish when it passes.
    apply_changes_orchestrator: Factory[
        OrchestratorContract[ApplyChangesCommand, ApplyChangesView]
    ] = Factory(
        ApplyChangesOrchestrator,
        start_apply_changes=apply_use_cases.start_apply_changes_use_case,
        assemble_assistant_version=assistant_use_cases.assemble_assistant_version_use_case,
        check_applied_version=apply_use_cases.check_applied_version_use_case,
        start_autotest_run=autotest_use_cases.start_autotest_run_use_case,
        enqueue_autotest_run=autotest_use_cases.enqueue_autotest_run_use_case,
        publish_applied_version=apply_use_cases.publish_applied_version_use_case,
        fail_apply_changes=apply_use_cases.fail_apply_changes_use_case,
        get_apply_changes=apply_use_cases.get_apply_changes_use_case,
    )
    get_apply_changes_orchestrator = use_case_orchestrator(
        apply_use_cases.get_apply_changes_use_case
    )

    # --- Assistant versions and autotests.
    assemble_assistant_version_orchestrator = use_case_orchestrator(
        assistant_use_cases.assemble_assistant_version_use_case
    )
    list_assistant_versions_orchestrator = use_case_orchestrator(
        assistant_use_cases.list_assistant_versions_use_case
    )
    get_assistant_version_orchestrator = use_case_orchestrator(
        assistant_use_cases.get_assistant_version_use_case
    )
    get_autotest_run_orchestrator = use_case_orchestrator(
        autotest_use_cases.get_autotest_run_use_case
    )
    get_go_live_readiness_orchestrator = use_case_orchestrator(
        assistant_use_cases.get_go_live_readiness_use_case
    )
    publish_assistant_version_orchestrator = use_case_orchestrator(
        assistant_use_cases.publish_assistant_version_use_case
    )
    rollback_assistant_version_orchestrator = use_case_orchestrator(
        assistant_use_cases.rollback_assistant_version_use_case
    )
