from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.spend_guard_use_cases import (
    admit_owner_action_factory,
)
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_commands import (
    AssistantVersionQuery,
    RunAutotestsCommand,
)
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseCommand,
    AutotestCaseList,
    AutotestCaseView,
    CreateAutotestCaseCommand,
    ListAutotestCasesQuery,
    OwnerCheckOutcomeView,
    OwnerCheckProbeCommand,
    OwnerCheckProbeOutcome,
    OwnerCheckProbeStart,
    UpdateAutotestCaseCommand,
)
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
from app.use_cases.autotests.cases.create_autotest_case_use_case import (
    CreateAutotestCaseUseCase,
)
from app.use_cases.autotests.cases.delete_autotest_case_use_case import (
    DeleteAutotestCaseUseCase,
)
from app.use_cases.autotests.cases.list_autotest_cases_use_case import (
    ListAutotestCasesUseCase,
)
from app.use_cases.autotests.cases.prepare_owner_check_probe_use_case import (
    PrepareOwnerCheckProbeUseCase,
)
from app.use_cases.autotests.cases.record_owner_check_probe_use_case import (
    RecordOwnerCheckProbeUseCase,
)
from app.use_cases.autotests.cases.update_autotest_case_use_case import (
    UpdateAutotestCaseUseCase,
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

    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    plan_autotest_scenarios_use_case: Factory[
        UseCaseContract[AutotestPlanningRequest, AutotestScenarioPlanning]
    ] = Factory(
        PlanAutotestScenariosUseCase,
        business_profile_repo=repositories.business_profile_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        autotest_case_repo=repositories.autotest_case_repo,
        niche_template_registry=registries.niche_template_registry,
        language_registry=registries.language_registry,
        critical_samples=config.app_settings.provided.quality.autotest_critical_samples,
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
        admit_owner_action=admit_owner_action_factory(registries, time_provider),
        assistant_apply_repo=repositories.assistant_apply_repo,
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

    # --- The owner's own checks ("My checks").
    list_autotest_cases_use_case: Factory[
        UseCaseContract[ListAutotestCasesQuery, AutotestCaseList]
    ] = Factory(
        ListAutotestCasesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        autotest_case_repo=repositories.autotest_case_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        autotest_run_repo=repositories.autotest_run_repo,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    create_autotest_case_use_case: Factory[
        UseCaseContract[CreateAutotestCaseCommand, AutotestCaseView]
    ] = Factory(
        CreateAutotestCaseUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        autotest_case_repo=repositories.autotest_case_repo,
        conversation_repo=repositories.conversation_repo,
        conversation_review_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        unanswered_question_repo=repositories.unanswered_question_repo,
        language_detector=utilities.language_detector,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    update_autotest_case_use_case: Factory[
        UseCaseContract[UpdateAutotestCaseCommand, AutotestCaseView]
    ] = Factory(
        UpdateAutotestCaseUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        autotest_case_repo=repositories.autotest_case_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    prepare_owner_check_probe_use_case: Factory[
        UseCaseContract[OwnerCheckProbeCommand, OwnerCheckProbeStart]
    ] = Factory(
        PrepareOwnerCheckProbeUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        autotest_case_repo=repositories.autotest_case_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        language_registry=registries.language_registry,
        rate_limit_registry=registries.request_rate_limit_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_owner_check_probe_use_case: Factory[
        UseCaseContract[OwnerCheckProbeOutcome, OwnerCheckOutcomeView]
    ] = Factory(
        RecordOwnerCheckProbeUseCase,
        autotest_case_repo=repositories.autotest_case_repo,
        localized_text_resolver=utilities.localized_text_resolver,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_autotest_case_use_case: Factory[
        UseCaseContract[AutotestCaseCommand, None]
    ] = Factory(
        DeleteAutotestCaseUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        autotest_case_repo=repositories.autotest_case_repo,
    )
