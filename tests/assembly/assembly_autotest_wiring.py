"""Version, autotest and background worker use cases of the assembly testbed."""

from collections.abc import Sequence

from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.assistants.queue_autotest_run_orchestrator import (
    QueueAutotestRunOrchestrator,
)
from app.orchestrators.assistants.run_autotests_orchestrator import (
    RunAutotestsOrchestrator,
)
from app.orchestrators.assistants.run_queued_autotests_orchestrator import (
    RunQueuedAutotestsOrchestrator,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.transformers.assembly.assistant_instruction_transformer import (
    AssistantInstructionTransformer,
)
from app.transformers.assembly.assistant_version_details_transformer import (
    AssistantVersionDetailsTransformer,
)
from app.transformers.assembly.assistant_version_summary_transformer import (
    AssistantVersionSummaryTransformer,
)
from app.transformers.assembly.autotest_run_view_transformer import (
    AutotestRunViewTransformer,
)
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from app.transformers.assembly.phone_instruction_transformer import (
    PhoneInstructionTransformer,
)
from app.use_cases.assistants.assemble_assistant_version_use_case import (
    AssembleAssistantVersionUseCase,
)
from app.use_cases.assistants.get_assistant_version_use_case import (
    GetAssistantVersionUseCase,
)
from app.use_cases.assistants.list_assistant_versions_use_case import (
    ListAssistantVersionsUseCase,
)
from app.use_cases.assistants.pending_changes.build_assistant_draft_use_case import (
    BuildAssistantDraftUseCase,
)
from app.use_cases.assistants.pending_changes.collect_pending_changes_use_case import (
    CollectPendingChangesUseCase,
)
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
)
from app.use_cases.autotests.abandon_autotest_run_use_case import (
    AbandonAutotestRunUseCase,
)
from app.use_cases.autotests.enqueue_autotest_run_use_case import (
    RUN_AUTOTESTS_JOB,
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
from app.use_cases.autotests.run_autotest_scenario_use_case import (
    RunAutotestScenarioUseCase,
)
from app.use_cases.autotests.start_autotest_run_use_case import StartAutotestRunUseCase
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.assembly.assembly_scripted_models import AssemblyScriptedModels
from tests.assembly.deferred_use_case import DeferredUseCase
from tests.foundation.access_support import ACCESS_SETTINGS
from tests.live_events.recording_event_publisher import RecordingEventPublisher


class AssemblyAutotestWiring(AssemblyScriptedModels):
    """The scripted slice with its version, autotest and worker use cases."""

    def _build_autotest_use_cases(
        self,
        price_question_limit: PriceQuestionScenarioLimit,
        llm_token_prices: Sequence[LlmTokenPrice],
    ) -> None:
        authorize = self.authorize = AuthorizeBusinessAccessUseCase(
            self.business_repo,
            self.user_repo,
            self.audit_repo,
            self.wall_clock,
            session_assurance=SessionAssuranceContext(),
            app_settings=ACCESS_SETTINGS,
        )
        details_transformer = self.details_transformer = (
            AssistantVersionDetailsTransformer()
        )
        run_view_transformer = AutotestRunViewTransformer()
        self.build_draft_use_case = BuildAssistantDraftUseCase(
            business_profile_repo=self.profile_repo,
            knowledge_item_repo=self.knowledge_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            country_registry=self.country_registry,
            language_registry=self.language_registry,
            niche_template_registry=self.niche_registry,
            plan_registry=self.plan_registry,
            business_facts_transformer=BusinessFactsTransformer(),
            assistant_instruction_transformer=AssistantInstructionTransformer(),
            phone_instruction_transformer=PhoneInstructionTransformer(),
            wall_clock=self.wall_clock,
        )
        self.collect_pending_changes_use_case = CollectPendingChangesUseCase(
            self.build_draft_use_case,
            AssistantInstructionTransformer(),
            LocalizedTextResolver(),
        )
        self.assemble_use_case = AssembleAssistantVersionUseCase(
            authorize_business_access=authorize,
            business_repo=self.business_repo,
            assistant_version_repo=self.version_repo,
            build_assistant_draft=self.build_draft_use_case,
            version_details_transformer=details_transformer,
            app_settings=self.settings,
            wall_clock=self.wall_clock,
        )
        self.list_versions_use_case = ListAssistantVersionsUseCase(
            authorize,
            self.version_repo,
            AssistantVersionSummaryTransformer(),
        )
        self.get_version_use_case = GetAssistantVersionUseCase(
            authorize,
            self.version_repo,
            details_transformer,
        )
        plan_scenarios = PlanAutotestScenariosUseCase(
            business_profile_repo=self.profile_repo,
            knowledge_item_repo=self.knowledge_repo,
            resource_repo=self.resource_repo,
            niche_template_registry=self.niche_registry,
            language_registry=self.language_registry,
            price_question_limit=price_question_limit,
        )
        self.autotest_events = RecordingEventPublisher()
        self.start_autotest_run_use_case = StartAutotestRunUseCase(
            authorize_business_access=authorize,
            assistant_version_repo=self.version_repo,
            autotest_run_repo=self.run_repo,
            plan_autotest_scenarios=plan_scenarios,
            live_events=self.autotest_events,
            wall_clock=self.wall_clock,
        )
        self.run_scenario_use_case = RunAutotestScenarioUseCase(
            conversation_turn_orchestrator=self.conversation,
            customer_llm_adapter=self.customer_llm,
            judge_llm_adapter=self.judge_llm,
            message_repo=self.message_repo,
            app_settings=self.settings,
            llm_token_prices=llm_token_prices or DEFAULT_LLM_TOKEN_PRICES,
        )
        self.finish_autotest_run_use_case = FinishAutotestRunUseCase(
            self.version_repo,
            self.run_repo,
            run_view_transformer,
            self.autotest_events,
            self.wall_clock,
        )
        self.get_autotest_run_use_case = GetAutotestRunUseCase(
            authorize,
            self.version_repo,
            self.run_repo,
            run_view_transformer,
        )
        self.run_autotests_orchestrator = RunAutotestsOrchestrator(
            self.start_autotest_run_use_case,
            self.run_scenario_use_case,
            self.finish_autotest_run_use_case,
        )
        # The production path: the request starts a run, the worker plays it.
        self.enqueue_autotest_run_use_case = EnqueueAutotestRunUseCase(
            self.run_repo,
            JobQueueFacilitator(
                self.job_repo, self.wall_clock, self.job_stores.job_wakeup
            ),
            run_view_transformer,
        )
        self.queue_autotest_run_orchestrator = QueueAutotestRunOrchestrator(
            self.start_autotest_run_use_case,
            self.enqueue_autotest_run_use_case,
        )
        self.resume_autotest_run_use_case = ResumeAutotestRunUseCase(
            self.business_repo,
            self.version_repo,
            self.run_repo,
            plan_scenarios,
        )
        self.abandon_autotest_run_use_case = AbandonAutotestRunUseCase(
            self.version_repo,
            self.run_repo,
            self.autotest_events,
            self.wall_clock,
        )
        self.record_autotest_progress_use_case = RecordAutotestProgressUseCase(
            self.run_repo,
            self.autotest_events,
            self.wall_clock,
        )
        # "Apply changes" goes on after the checks; wired with publishing.
        self.publish_applied_later: DeferredUseCase[AppliedVersion, None] = (
            DeferredUseCase()
        )
        self.run_queued_autotests_orchestrator = RunQueuedAutotestsOrchestrator(
            self.resume_autotest_run_use_case,
            self.run_scenario_use_case,
            self.finish_autotest_run_use_case,
            self.abandon_autotest_run_use_case,
            self.record_autotest_progress_use_case,
            self.publish_applied_later,
        )
        self.worker = self.background_worker(
            {
                RUN_AUTOTESTS_JOB: PipelineOperator(
                    OrchestratorPipeline(self.run_queued_autotests_orchestrator)
                )
            }
        )
