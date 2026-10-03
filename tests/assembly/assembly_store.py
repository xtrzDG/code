"""The assembly testbed's storage: clock, settings, users, repositories, registries."""

from collections.abc import Mapping
from datetime import UTC, datetime

from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.jobs import QueuedJobOperator, QueuedJobRepoContract
from app.gateways.worker.background_worker import BackgroundWorker
from app.registries.billing.plan_registry import PlanRegistry
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
from app.repositories.billing_repositories import (
    InvoiceRepository,
    SubscriptionRepository,
)
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.conversation_repositories import MessageRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.setup_repositories import (
    ActivationEventRepository,
    AssistantApplyRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.setup import ActivationEventDocument, AssistantApplyDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.job_queue import QueuedJobPageQuery
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import (
    PageSize,
    WorkerPollSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.assembly.fake_locale_registries import (
    FakeCountryRegistry,
    FakeLanguageRegistry,
)
from tests.assembly.fake_niche_templates import FakeNicheTemplateRegistry
from tests.platform.worker_fakes import (
    TEST_LANE_CONCURRENCY,
    JobStores,
    build_job_stores,
)

# Thursday 1 October 2026, 09:00 UTC (13:00 in Tbilisi, 18:00 in Tokyo).
START_MOMENT: datetime = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
NANOSECONDS_PER_SECOND: int = 1_000_000_000
DEFAULT_ENVIRONMENT: dict[str, str] = {
    "LLM_PROVIDER": "scripted",
    "APP_BASE_URL": "https://api.example.com",
    "AUTOTEST_TURN_LIMIT": "3",
}


class RecordingErrorReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


class AssemblyStore:
    """Clock, settings, users, in-memory repositories and registries."""

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
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
        self.invoice_repo = InvoiceRepository(
            InMemoryDocumentCollectionAdapter(InvoiceDocument)
        )
        self.activation_event_repo = ActivationEventRepository(
            InMemoryDocumentCollectionAdapter(ActivationEventDocument)
        )
        self.apply_repo = AssistantApplyRepository(
            InMemoryDocumentCollectionAdapter(AssistantApplyDocument)
        )
        self.job_stores: JobStores = build_job_stores()
        self.job_repo: QueuedJobRepoContract = self.job_stores.job_repo
        self.worker_errors = RecordingErrorReporter()

        self.niche_registry = FakeNicheTemplateRegistry()
        self.country_registry = FakeCountryRegistry()
        self.language_registry = FakeLanguageRegistry()
        self.plan_registry = PlanRegistry()

    def advance(self, seconds: int) -> None:
        self.now_seconds += seconds

    def pending_jobs(self) -> list[QueuedJobDocument]:
        """Queued jobs still waiting for a (first or repeated) attempt."""

        return self.job_repo.list_page(
            QueuedJobPageQuery(status=QueuedJobStatus.PENDING, page_size=PageSize(200))
        )

    def background_worker(
        self,
        queued_job_operators: Mapping[JobName, QueuedJobOperator],
    ) -> BackgroundWorker:
        """A worker over this testbed's job queue and clock."""

        return BackgroundWorker(
            periodic_jobs=[],
            queued_job_operators=queued_job_operators,
            job_repo=self.job_repo,
            periodic_run_repo=self.job_stores.periodic_run_repo,
            wall_clock=self.wall_clock,
            error_reporter=self.worker_errors,
            poll_seconds=WorkerPollSeconds(5),
            storage_scope=StorageScopeContext(),
            job_wakeup=self.job_stores.job_wakeup,
            lane_concurrency=TEST_LANE_CONCURRENCY,
        )

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
