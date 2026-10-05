"""
The platform's operations wired in memory: the collections the system page
and the alerts read, their repositories, the shared signal counters and a
clock the tests move.
"""

from collections.abc import Sequence

from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds, WallClock

from app.adapters.monitoring.bucket_signal_counter_adapter import (
    BucketSignalCounterAdapter,
)
from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.maintenance_run_repository import MaintenanceRunRepository
from app.repositories.platform_activity_repository import PlatformActivityRepository
from app.repositories.platform_alert_state_repository import (
    PlatformAlertStateRepository,
)
from app.repositories.quality_repositories import QualityTotalsRepository
from app.repositories.spend_guard_repositories import UsageSpendRepository
from app.repositories.system_health_repository import SystemHealthRepository
from app.schemas.configurations.platform_alert_settings import PlatformAlertSettings
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.jobs import QueuedJobDocument, WorkerHeartbeatDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.monitoring.constrained_integers import AlertCooldownMinutes
from app.schemas.typings.monitoring.constrained_strings import AlertChatId
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.schemas.typings.spend.constrained_integers import (
    PlatformDailySpendBudgetMicroUsd,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.alerts.alert_checks import PlatformAlertChecks
from app.use_cases.admin.alerts.check_platform_alerts_use_case import (
    CheckPlatformAlertsUseCase,
)
from app.use_cases.admin.alerts.spend_alert_checks import SpendAlertChecks
from tests.knowledge.website_import.recording_job_queue import RecordingJobQueue
from tests.platform_ops.ops_documents import NOW

ADMIN: UserId = UserId()
ALERT_CHAT: AlertChatId = AlertChatId("-1001234567890")
ALERT_EMAIL: EmailAddress = EmailAddress("oncall@workshop.example")
CABINET: CabinetBaseUrl = CabinetBaseUrl("https://cabinet.workshop.example")


def put[Stored: BaseDocument](
    collection: DocumentCollectionAdapterContract[Stored], *documents: Stored
) -> None:
    """Store documents under their ids."""

    for document in documents:
        collection.upsert(str(vars(document)["id"]), document)


class AdminsOnly(UseCaseContract[PlatformAdminAccessRequest, UserDocument]):
    """The platform admin check: ADMIN passes, everyone else is refused."""

    def run(self, input_data: PlatformAdminAccessRequest) -> UserDocument:
        if input_data.user_id != ADMIN:
            raise AccessDeniedError("Platform admins only.")
        return UserDocument.model_construct(id=ADMIN)


class OpsClock:
    """A wall clock the test moves forward."""

    def __init__(self, start: Microseconds = NOW) -> None:
        self.now: int = int(start)
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )

    def advance(self, microseconds: int) -> None:
        self.now += microseconds


class OpsWorld:
    """Collections, repositories and counters of one in-memory platform."""

    def __init__(self) -> None:
        self.clock = OpsClock()
        self.jobs = InMemoryDocumentCollectionAdapter[QueuedJobDocument](
            QueuedJobDocument
        )
        self.pulses = InMemoryDocumentCollectionAdapter[WorkerHeartbeatDocument](
            WorkerHeartbeatDocument
        )
        self.channels = InMemoryDocumentCollectionAdapter[ChannelDocument](
            ChannelDocument
        )
        self.businesses = InMemoryDocumentCollectionAdapter[BusinessDocument](
            BusinessDocument
        )
        self.handoffs = InMemoryDocumentCollectionAdapter[HandoffDocument](
            HandoffDocument
        )
        self.outbox = InMemoryDocumentCollectionAdapter[OutboundMessageDocument](
            OutboundMessageDocument
        )
        self.messages = InMemoryDocumentCollectionAdapter[MessageDocument](
            MessageDocument
        )
        self.quality_scores = InMemoryDocumentCollectionAdapter[
            ConversationQualityScoreDocument
        ](ConversationQualityScoreDocument)
        self.alert_states = InMemoryDocumentCollectionAdapter[
            PlatformAlertStateDocument
        ](PlatformAlertStateDocument)
        self.runs = InMemoryDocumentCollectionAdapter[MaintenanceRunDocument](
            MaintenanceRunDocument
        )
        self.health_repo = SystemHealthRepository(
            self.jobs, self.pulses, self.channels, self.businesses
        )
        self.activity_repo = PlatformActivityRepository(
            self.handoffs, self.outbox, self.messages
        )
        self.alert_state_repo = PlatformAlertStateRepository(self.alert_states)
        self.run_repo = MaintenanceRunRepository(self.runs)
        self.buckets = InMemoryRateLimitBucketAdapter()
        self.signals = BucketSignalCounterAdapter(self.buckets, self.clock.wall_clock)
        self.queue = RecordingJobQueue()
        self.usage_events = InMemoryDocumentCollectionAdapter[UsageEventDocument](
            UsageEventDocument
        )
        self.spend_budget: PlatformDailySpendBudgetMicroUsd | None = None

    def checks(self) -> PlatformAlertChecks:
        return PlatformAlertChecks(
            system_health_repo=self.health_repo,
            platform_activity_repo=self.activity_repo,
            signal_counter=self.signals,
            quality_totals_repo=QualityTotalsRepository(self.quality_scores),
            spend_checks=SpendAlertChecks(
                UsageSpendRepository(self.usage_events), self.spend_budget
            ),
        )

    def alerts_use_case(
        self,
        cooldown_minutes: int = 60,
        chat_ids: Sequence[AlertChatId] = (ALERT_CHAT,),
        emails: Sequence[EmailAddress] = (ALERT_EMAIL,),
    ) -> CheckPlatformAlertsUseCase:
        return CheckPlatformAlertsUseCase(
            checks=self.checks(),
            state_repo=self.alert_state_repo,
            job_queue=self.queue,
            alert_settings=PlatformAlertSettings(
                telegram_chat_ids=list(chat_ids),
                emails=list(emails),
                cooldown_minutes=AlertCooldownMinutes(cooldown_minutes),
            ),
            cabinet_base_url=CABINET,
            wall_clock=self.clock.wall_clock,
        )
