from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_commands import (
    AssistantVersionQuery,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestPlanningRequest,
    AutotestRunCompletion,
    AutotestRunFailure,
    AutotestRunPlan,
    AutotestRunProgress,
    AutotestScenarioPlanning,
)
from app.schemas.dto.jobs import (
    QueuedJobInput,
)
from app.use_cases.autotests.abandon_autotest_run_use_case import (
    AbandonAutotestRunUseCase,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import (
    EnqueueAutotestRunUseCase,
)
from app.use_cases.autotests.finish_autotest_run_use_case import (
    FinishAutotestRunUseCase,
)
from app.use_cases.autotests.get_autotest_run_use_case import GetAutotestRunUseCase
from app.use_cases.autotests.plan_autotest_scenarios_use_case import (
    PlanAutotestScenariosUseCase,
)
from app.use_cases.autotests.record_autotest_progress_use_case import (
    RecordAutotestProgressUseCase,
)
from app.use_cases.autotests.resume_autotest_run_use_case import (
    ResumeAutotestRunUseCase,
)
from app.use_cases.autotests.start_autotest_run_use_case import StartAutotestRunUseCase


class AutotestUseCasesContainer(containers.DeclarativeContainer):
    """
    Autotest runs of an assistant version: planning, starting, queueing,
    resuming, progress and results. The scenario runner drives the conversation
    turn orchestrator, so it is wired with the orchestrators.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    plan_autotest_scenarios_use_case: Factory[
        UseCaseContract[AutotestPlanningRequest, AutotestScenarioPlanning]
    ] = Factory(
        PlanAutotestScenariosUseCase,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        niche_template_registry=registries.niche_template_registry,
        language_registry=registries.language_registry,
    )
    start_autotest_run_use_case: Factory[
        UseCaseContract[RunAutotestsCommand, AutotestRunPlan]
    ] = Factory(
        StartAutotestRunUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        plan_autotest_scenarios=plan_autotest_scenarios_use_case,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    enqueue_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunPlan, AutotestRunView]
    ] = Factory(
        EnqueueAutotestRunUseCase,
        autotest_run_repo=repositories.autotest_run_repo,
        job_queue=facilitators.job_queue_facilitator,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
    )
    resume_autotest_run_use_case: Factory[
        UseCaseContract[QueuedJobInput, AutotestRunPlan]
    ] = Factory(
        ResumeAutotestRunUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        plan_autotest_scenarios=plan_autotest_scenarios_use_case,
    )
    abandon_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunFailure, None]
    ] = Factory(
        AbandonAutotestRunUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_autotest_progress_use_case: Factory[
        UseCaseContract[AutotestRunProgress, None]
    ] = Factory(
        RecordAutotestProgressUseCase,
        autotest_run_repo=repositories.autotest_run_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    finish_autotest_run_use_case: Factory[
        UseCaseContract[AutotestRunCompletion, AutotestRunView]
    ] = Factory(
        FinishAutotestRunUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_autotest_run_use_case: Factory[
        UseCaseContract[AssistantVersionQuery, AutotestRunView]
    ] = Factory(
        GetAutotestRunUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        autotest_run_view_transformer=transformers.autotest_run_view_transformer,
    )
