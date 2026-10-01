"""In-memory wiring of the assembly slice, shared by its tests.

Everything the slice depends on is either an in-memory repository or a
fake; the AI customer and the judge are ScriptedLlmAdapter instances whose
answers tests can program per scenario key.
"""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from typed_time_provider import Microseconds, WallClock

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.llm import LlmAdapterContract
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.gateways.http.assistant_routes import build_assistant_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.worker.background_worker import BackgroundWorker, WorkerTickReport
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
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.assistants.assemble_assistant_version_pipeline import (
    AssembleAssistantVersionPipeline,
)
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.plan_registry import PlanRegistry
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
from app.repositories.billing_repositories import SubscriptionRepository
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.conversation_repositories import MessageRepository
from app.repositories.job_repositories import QueuedJobRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import (
    AuditLogEntryDocument,
    DpaAcceptanceDocument,
)
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.assistants import (
    AssembleAssistantVersionCommand,
    AssembleAssistantVersionRequest,
    AssistantVersionDetails,
    AutotestRunView,
    LlmTokenPrice,
    PublishAssistantVersionCommand,
    RunAutotestsCommand,
)
from app.schemas.dto.conversations import AssistantReply, InboundMessage, LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import (
    PriceQuestionScenarioLimit,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import WorkerPollSeconds
from app.schemas.typings.users.prefixed_id import UserId
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
from app.use_cases.assistants.activate_assistant_version_use_case import (
    ActivateAssistantVersionUseCase,
)
from app.use_cases.assistants.assemble_assistant_version_use_case import (
    AssembleAssistantVersionUseCase,
)
from app.use_cases.assistants.check_go_live_readiness_use_case import (
    CheckGoLiveReadinessUseCase,
)
from app.use_cases.assistants.get_assistant_version_use_case import (
    GetAssistantVersionUseCase,
)
from app.use_cases.assistants.list_assistant_versions_use_case import (
    ListAssistantVersionsUseCase,
)
from app.use_cases.assistants.publish_assistant_version_use_case import (
    PublishAssistantVersionUseCase,
)
from app.use_cases.assistants.rollback_assistant_version_use_case import (
    RollbackAssistantVersionUseCase,
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
from app.use_cases.autotests.resume_autotest_run_use_case import (
    ResumeAutotestRunUseCase,
)
from app.use_cases.autotests.run_autotest_scenario_use_case import (
    RunAutotestScenarioUseCase,
)
from app.use_cases.autotests.start_autotest_run_use_case import (
    StartAutotestRunUseCase,
)
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.assembly.fakes import (
    FakeAssistantToolCatalog,
    FakeAuthenticationOperator,
    FakeCallGreetingUseCase,
    FakeConversationTurnOrchestrator,
    FakeCountryRegistry,
    FakeLanguageRegistry,
    FakeNicheTemplateRegistry,
    FakeVoiceAgentProvisioner,
    TokenReportingLlmAdapter,
    count_assistant_turns,
    read_last_user_text,
)

# Thursday 1 October 2026, 09:00 UTC (13:00 in Tbilisi, 18:00 in Tokyo).
START_MOMENT: datetime = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
NANOSECONDS_PER_SECOND: int = 1_000_000_000
DEFAULT_ENVIRONMENT: dict[str, str] = {
    "LLM_PROVIDER": "scripted",
    "APP_BASE_URL": "https://api.example.com",
    "AUTOTEST_TURN_LIMIT": "3",
}
CHANNEL_USER_PATTERN: re.Pattern[str] = re.compile(
    r"^autotest-autotest_run_[0-9a-f\-]{36}-(?P<key>[a-z0-9_\-]+)$"
)
LANGUAGE_TAG_PATTERN: re.Pattern[str] = re.compile(r"language tag ([A-Za-z\-]+)\)")
SCENARIO_LINE_PATTERN: re.Pattern[str] = re.compile(r"^Scenario: (\S+) ", re.MULTILINE)
DONE: str = "[DONE]"
CUSTOMER_TEXTS: dict[str, str] = {
    "ka": "გამარჯობა, მინდა მაგიდის დაჯავშნა ხვალ",
    "ru": "Здравствуйте, хочу забронировать стол на завтра",
    "en": "Hello, I would like to book a table for tomorrow",
    "it": "Buongiorno, vorrei prenotare un tavolo per domani",
    "ja": "こんにちは、明日の予約をお願いします",
    "he": "שלום, אני רוצה לקבוע תור למחר",
    "ar": "مرحبا، أريد حجز موعد غدا",
}
ASSISTANT_TEXTS: dict[str, str] = {
    "ka": "გამარჯობა! მე ვარ AI ასისტენტი. როგორ დაგეხმაროთ?",
    "ru": "Здравствуйте! Я AI-ассистент. Чем могу помочь?",
    "en": "Hello! I am the AI assistant. How can I help?",
    "it": "Buongiorno! Sono l'assistente AI. Come posso aiutarla?",
    "ja": "こんにちは！AIアシスタントです。ご用件をどうぞ。",
    "he": "שלום! אני עוזר בינה מלאכותית. איך אפשר לעזור?",
    "ar": "مرحبا! أنا المساعد الذكي. كيف يمكنني مساعدتك؟",
}
PERFECT_SCORES: dict[str, int] = {
    "facts_and_prices": 5,
    "booking_data": 5,
    "ai_disclosure": 5,
    "handoff": 5,
    "language": 5,
}

type CustomerScript = Callable[[LlmRequest, int], str]
type ReplyScript = Callable[[InboundMessage, str, int], AssistantReply]


def read_scenario_key(message: InboundMessage) -> str:
    """Scenario key encoded in the autotest channel user id."""

    match: re.Match[str] | None = CHANNEL_USER_PATTERN.match(
        str(message.channel_user_id)
    )
    assert match is not None, message.channel_user_id
    return match.group("key")


def read_scenario_language(scenario_key: str) -> str:
    return scenario_key.split("__")[1]


def read_scenario_kind(scenario_key: str) -> AutotestScenarioKind:
    return AutotestScenarioKind(scenario_key.split("__")[0])


def default_customer_script(request: LlmRequest, turn_index: int) -> str:
    """One message in the scenario language, then [DONE]."""

    if turn_index >= 1:
        return DONE

    match: re.Match[str] | None = LANGUAGE_TAG_PATTERN.search(
        str(request.system_prompt)
    )
    assert match is not None
    return CUSTOMER_TEXTS[match.group(1)]


def default_reply_script(
    message: InboundMessage,
    scenario_key: str,
    turn_index: int,
) -> AssistantReply:
    """
    Replies in the scenario language; books in BOOKING scenarios and hands
    off in HUMAN_REQUEST and EMERGENCY scenarios.
    """

    del turn_index
    language: str = read_scenario_language(scenario_key)
    kind: AutotestScenarioKind = read_scenario_kind(scenario_key)
    is_handed_off: bool = kind in (
        AutotestScenarioKind.HUMAN_REQUEST,
        AutotestScenarioKind.EMERGENCY,
    )
    del message
    return build_reply(
        language,
        is_handed_off=is_handed_off,
        is_booked=kind is AutotestScenarioKind.BOOKING,
    )


def build_reply(
    language: str,
    *,
    text: str | None = None,
    is_handed_off: bool = False,
    is_booked: bool = False,
    is_lead_created: bool = False,
) -> AssistantReply:
    """An assistant reply in a scenario language (key spelling, e.g. "ka")."""

    return AssistantReply(
        conversation_id=ConversationId(),
        text=MessageText(text if text is not None else ASSISTANT_TEXTS[language]),
        language=LanguageTag(language),
        is_handed_off=is_handed_off,
        created_booking_ids=[BookingId()] if is_booked else [],
        created_lead_ids=[LeadId()] if is_lead_created else [],
        created_handoff_ids=[HandoffId()] if is_handed_off else [],
    )


class RecordingErrorReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


class AssemblyTestbed:
    """
    The slice wired over in-memory repositories, with fakes for registries,
    the conversation engine, the voice platform and the call greeting.

    Program the autotests through:
    - `customer_script` (default: one message in the scenario language, then
      [DONE]);
    - `reply_scripts[scenario_key]` (default: `default_reply_script`);
    - `judge_scores[scenario_key]` and `judge_raw_answers[scenario_key]`
      (default: 5 on every criterion).
    """

    def __init__(
        self,
        environment: Mapping[str, str] | None = None,
        price_question_limit: int = 10,
        llm_token_prices: Sequence[LlmTokenPrice] = (),
        customer_token_usage: tuple[int, int] | None = None,
        judge_token_usage: tuple[int, int] | None = None,
        reply_cost: int = 0,
    ) -> None:
        self.now_seconds: int = int(START_MOMENT.timestamp())
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now_seconds * NANOSECONDS_PER_SECOND,
        )
        self.settings: AppSettings = assemble_app_settings(
            {**DEFAULT_ENVIRONMENT, **(environment or {})}
        )
        self.owner_id: UserId = UserId()
        self.staff_id: UserId = UserId()
        self.stranger_id: UserId = UserId()

        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter(BusinessDocument)
        )
        self.profile_repo = BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter(BusinessProfileDocument)
        )
        self.knowledge_repo = KnowledgeItemRepository(
            InMemoryDocumentCollectionAdapter(KnowledgeItemDocument)
        )
        self.resource_repo = ResourceRepository(
            InMemoryDocumentCollectionAdapter(ResourceDocument)
        )
        self.exception_repo = ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter(ScheduleExceptionDocument)
        )
        self.version_repo = AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter(AssistantVersionDocument)
        )
        self.run_repo = AutotestRunRepository(
            InMemoryDocumentCollectionAdapter(AutotestRunDocument)
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter(MessageDocument)
        )
        self.user_repo = UserRepository(InMemoryDocumentCollectionAdapter(UserDocument))
        self.audit_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter(AuditLogEntryDocument)
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter(SubscriptionDocument)
        )
        self.dpa_repo = DpaAcceptanceRepository(
            InMemoryDocumentCollectionAdapter(DpaAcceptanceDocument)
        )
        self.job_repo = QueuedJobRepository(
            InMemoryDocumentCollectionAdapter(QueuedJobDocument)
        )
        self.worker_errors = RecordingErrorReporter()

        self.niche_registry = FakeNicheTemplateRegistry()
        self.country_registry = FakeCountryRegistry()
        self.language_registry = FakeLanguageRegistry()
        self.plan_registry = PlanRegistry()

        self.customer_script: CustomerScript = default_customer_script
        self.reply_scripts: dict[str, ReplyScript] = {}
        self.judge_scores: dict[str, dict[str, int]] = {}
        self.judge_raw_answers: dict[str, str] = {}
        self.judge_errors: set[str] = set()
        self.conversation = FakeConversationTurnOrchestrator(
            self._reply,
            self.message_repo,
            CostMicroUsd(reply_cost),
        )
        self.customer_requests = ScriptedLlmAdapter(self._customer_turn)
        self.judge_requests = ScriptedLlmAdapter(self._judge_turn)
        self.customer_llm: LlmAdapterContract = (
            TokenReportingLlmAdapter(self.customer_requests, *customer_token_usage)
            if customer_token_usage is not None
            else self.customer_requests
        )
        self.judge_llm: LlmAdapterContract = (
            TokenReportingLlmAdapter(self.judge_requests, *judge_token_usage)
            if judge_token_usage is not None
            else self.judge_requests
        )
        self.voice_provisioner = FakeVoiceAgentProvisioner()
        self.call_greeting = FakeCallGreetingUseCase()
        self.tool_catalog = FakeAssistantToolCatalog()
        self.authentication = FakeAuthenticationOperator()

        self._build_use_cases(
            PriceQuestionScenarioLimit(price_question_limit),
            llm_token_prices,
        )

    def _build_use_cases(
        self,
        price_question_limit: PriceQuestionScenarioLimit,
        llm_token_prices: Sequence[LlmTokenPrice],
    ) -> None:
        authorize = AuthorizeBusinessAccessUseCase(
            self.business_repo,
            self.user_repo,
            self.audit_repo,
            self.wall_clock,
        )
        details_transformer = AssistantVersionDetailsTransformer()
        run_view_transformer = AutotestRunViewTransformer()
        self.assemble_use_case = AssembleAssistantVersionUseCase(
            authorize_business_access=authorize,
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            knowledge_item_repo=self.knowledge_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            assistant_version_repo=self.version_repo,
            country_registry=self.country_registry,
            language_registry=self.language_registry,
            niche_template_registry=self.niche_registry,
            plan_registry=self.plan_registry,
            business_facts_transformer=BusinessFactsTransformer(),
            assistant_instruction_transformer=AssistantInstructionTransformer(),
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
            niche_template_registry=self.niche_registry,
            language_registry=self.language_registry,
            price_question_limit=price_question_limit,
        )
        self.start_autotest_run_use_case = StartAutotestRunUseCase(
            authorize_business_access=authorize,
            assistant_version_repo=self.version_repo,
            autotest_run_repo=self.run_repo,
            plan_autotest_scenarios=plan_scenarios,
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
        self.queue_autotest_run_orchestrator = QueueAutotestRunOrchestrator(
            self.start_autotest_run_use_case,
            EnqueueAutotestRunUseCase(
                self.run_repo,
                JobQueueFacilitator(self.job_repo, self.wall_clock),
                run_view_transformer,
            ),
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
            self.wall_clock,
        )
        self.run_queued_autotests_orchestrator = RunQueuedAutotestsOrchestrator(
            self.resume_autotest_run_use_case,
            self.run_scenario_use_case,
            self.finish_autotest_run_use_case,
            self.abandon_autotest_run_use_case,
        )
        self.worker = BackgroundWorker(
            periodic_jobs=[],
            queued_job_operators={
                RUN_AUTOTESTS_JOB: PipelineOperator(
                    OrchestratorPipeline(self.run_queued_autotests_orchestrator)
                )
            },
            job_repo=self.job_repo,
            wall_clock=self.wall_clock,
            error_reporter=self.worker_errors,
            poll_seconds=WorkerPollSeconds(5),
            storage_scope=StorageScopeContext(),
        )
        activate = ActivateAssistantVersionUseCase(
            check_go_live_readiness=CheckGoLiveReadinessUseCase(
                subscription_repo=self.subscription_repo,
                dpa_acceptance_repo=self.dpa_repo,
                business_profile_repo=self.profile_repo,
                knowledge_item_repo=self.knowledge_repo,
                resource_repo=self.resource_repo,
                niche_template_registry=self.niche_registry,
                app_settings=self.settings,
                wall_clock=self.wall_clock,
            ),
            business_repo=self.business_repo,
            assistant_version_repo=self.version_repo,
            voice_agent_provisioner=self.voice_provisioner,
            build_call_greeting=self.call_greeting,
            assistant_tool_catalog=self.tool_catalog,
            app_settings=self.settings,
            wall_clock=self.wall_clock,
        )
        self.publish_use_case = PublishAssistantVersionUseCase(
            authorize,
            self.version_repo,
            activate,
            details_transformer,
            self.user_repo,
            self.audit_repo,
            self.wall_clock,
        )
        self.rollback_use_case = RollbackAssistantVersionUseCase(
            authorize,
            self.version_repo,
            activate,
            details_transformer,
        )
        self.assemble_pipeline = AssembleAssistantVersionPipeline(
            UseCaseOrchestrator(self.assemble_use_case),
            self.run_autotests_orchestrator,
            UseCaseOrchestrator(self.get_version_use_case),
        )
        self.queued_assemble_pipeline = AssembleAssistantVersionPipeline(
            UseCaseOrchestrator(self.assemble_use_case),
            self.queue_autotest_run_orchestrator,
            UseCaseOrchestrator(self.get_version_use_case),
        )

    # Time.

    def advance(self, seconds: int) -> None:
        self.now_seconds += seconds

    # Shortcuts used by tests.

    def assemble(
        self,
        business_id: BusinessId,
        run_autotests: bool = False,
        user_id: UserId | None = None,
    ) -> AssistantVersionDetails:
        self.advance(60)
        return self.assemble_pipeline.start(
            AssembleAssistantVersionCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                request=AssembleAssistantVersionRequest(run_autotests=run_autotests),
            )
        )

    def run_autotests(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
        user_id: UserId | None = None,
    ) -> AutotestRunView:
        self.advance(60)
        return self.run_autotests_orchestrator.execute(
            RunAutotestsCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                version_id=version_id,
            )
        )

    def publish(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
        accept_failed_tests: bool = False,
        user_id: UserId | None = None,
    ) -> AssistantVersionDetails:
        self.advance(60)
        return self.publish_use_case.run(
            PublishAssistantVersionCommand(
                user_id=user_id or self.owner_id,
                business_id=business_id,
                version_id=version_id,
                accept_failed_tests=accept_failed_tests,
            )
        )

    def pending_jobs(self) -> list[QueuedJobDocument]:
        """Queued jobs still waiting for a (first or repeated) attempt."""

        return self.job_repo.list_due(Microseconds(2**62))

    def run_worker(self) -> WorkerTickReport:
        """One worker tick: plays every queued autotest run."""

        self.advance(60)
        return self.worker.run_once()

    def add_platform_admin(self) -> UserId:
        admin = UserDocument(
            login_method=LoginMethod.EMAIL,
            locale=LanguageTag("en"),
            is_verified=True,
            is_platform_admin=True,
        )
        self.user_repo.save(admin)
        return admin.id

    def version(
        self,
        business_id: BusinessId,
        version_id: AssistantVersionId,
    ) -> AssistantVersionDocument:
        version: AssistantVersionDocument | None = self.version_repo.get(
            business_id,
            version_id,
        )
        assert version is not None
        return version

    def business(self, business_id: BusinessId) -> BusinessDocument:
        business: BusinessDocument | None = self.business_repo.get(business_id)
        assert business is not None
        return business

    def build_client(self) -> TestClient:
        http_application = FastAPI()
        install_error_handlers(http_application)
        http_application.include_router(
            build_assistant_router(
                assemble_assistant_version_operator=PipelineOperator(
                    self.queued_assemble_pipeline
                ),
                list_assistant_versions_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.list_versions_use_case)
                    )
                ),
                get_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.get_version_use_case))
                ),
                get_autotest_run_operator=PipelineOperator(
                    OrchestratorPipeline(
                        UseCaseOrchestrator(self.get_autotest_run_use_case)
                    )
                ),
                run_autotests_operator=PipelineOperator(
                    OrchestratorPipeline(self.queue_autotest_run_orchestrator)
                ),
                publish_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.publish_use_case))
                ),
                rollback_assistant_version_operator=PipelineOperator(
                    OrchestratorPipeline(UseCaseOrchestrator(self.rollback_use_case))
                ),
                current_user=build_current_user_dependency(self.authentication),
            )
        )
        return TestClient(http_application)

    def bearer(self, user_id: UserId) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.authentication.register(user_id)}"}

    # Scripted model and conversation behaviour.

    def _customer_turn(self, request: LlmRequest) -> ScriptedLlmTurn:
        return ScriptedLlmTurn(
            text=MessageText(
                self.customer_script(request, count_assistant_turns(request))
            )
        )

    def _judge_turn(self, request: LlmRequest) -> ScriptedLlmTurn:
        match: re.Match[str] | None = SCENARIO_LINE_PATTERN.search(
            read_last_user_text(request)
        )
        assert match is not None
        scenario_key: str = match.group(1)
        if scenario_key in self.judge_errors:
            raise ExternalServiceError("Judge model is unavailable.")

        raw_answer: str | None = self.judge_raw_answers.get(scenario_key)
        if raw_answer is None:
            raw_answer = json.dumps(
                {
                    "scores": self.judge_scores.get(scenario_key, PERFECT_SCORES),
                    "notes": [f"Judged {scenario_key}."],
                }
            )

        return ScriptedLlmTurn(text=MessageText(raw_answer))

    def _reply(self, message: InboundMessage, turn_index: int) -> AssistantReply:
        scenario_key: str = read_scenario_key(message)
        script: ReplyScript = self.reply_scripts.get(scenario_key, default_reply_script)
        return script(message, scenario_key, turn_index)
