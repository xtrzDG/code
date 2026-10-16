"""The service level collections in memory, their sources and a clock."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.service_level_repositories import (
    ServiceLevelHourRepository,
    ServiceLevelSlotRepository,
    ServiceLevelSourceRepository,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_integers import (
    InboundProcessingAttemptCount,
)
from app.schemas.typings.platform.constrained_strings import JobName
from app.use_cases.observability.record_service_levels_use_case import (
    RecordServiceLevelsUseCase,
)
from app.utilities.deliveries.delivery_keys import derive_inbound_event_id
from tests.platform_ops.ops_world import OpsClock

SECOND: int = 1_000_000
MINUTE: int = 60 * SECOND
HOUR: int = 60 * MINUTE
DAY: int = 24 * HOUR
# A whole hour (and so a whole slot) in UTC.
HOUR_START: int = 1_791_187_200_000_000
BUSINESS: BusinessId = BusinessId()
TICK = JobTick(job_name=JobName("record_sli"), scheduled_at=Microseconds(0))


def inbound(
    created_at: int,
    answered_after: int | None,
    status: InboundEventStatus = InboundEventStatus.ANSWERED,
    kind: InboundEventKind = InboundEventKind.CUSTOMER_MESSAGE,
    business_id: BusinessId | None = BUSINESS,
    attempts: int = 1,
) -> InboundEventDocument:
    """A customer message received at `created_at`, processed after a wait."""

    provider_message_id = ProviderMessageId(f"update-{created_at}")
    return InboundEventDocument(
        id=derive_inbound_event_id(
            business_id, ChannelKind.TELEGRAM, provider_message_id
        ),
        business_id=business_id,
        kind=kind,
        channel=ChannelKind.TELEGRAM,
        provider_message_id=provider_message_id,
        attempts=InboundProcessingAttemptCount(attempts),
        status=(status if answered_after is not None else InboundEventStatus.RECEIVED),
        processed_at=(
            None
            if answered_after is None
            else Microseconds(created_at + answered_after)
        ),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


def reply(created_at: int, latency_ms: int | None) -> MessageDocument:
    """An assistant reply stored at `created_at` after a measured wait."""

    return MessageDocument(
        conversation_id=ConversationId(),
        business_id=BUSINESS,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.ASSISTANT,
        text=MessageText("We are open until 19:00."),
        channel=ChannelKind.TELEGRAM,
        reply_latency_ms=(
            None if latency_ms is None else ReplyLatencyMilliseconds(latency_ms)
        ),
        created_at=Microseconds(created_at),
        updated_at=Microseconds(created_at),
    )


class SliWorld:
    """Slots, hours, inbox events and messages of one in-memory platform."""

    def __init__(self, now: int = HOUR_START) -> None:
        self.clock = OpsClock(Microseconds(now))
        self.slots = InMemoryDocumentCollectionAdapter[ServiceLevelSlotDocument](
            ServiceLevelSlotDocument
        )
        self.hours = InMemoryDocumentCollectionAdapter[ServiceLevelHourDocument](
            ServiceLevelHourDocument
        )
        self.events = InMemoryDocumentCollectionAdapter[InboundEventDocument](
            InboundEventDocument
        )
        self.messages = InMemoryDocumentCollectionAdapter[MessageDocument](
            MessageDocument
        )
        self.slot_repo = ServiceLevelSlotRepository(self.slots)
        self.hour_repo = ServiceLevelHourRepository(self.hours)
        self.source_repo = ServiceLevelSourceRepository(self.events, self.messages)

    @property
    def now(self) -> int:
        return self.clock.now

    def receive(self, *events: InboundEventDocument) -> None:
        for event in events:
            self.events.upsert(str(event.id), event)

    def answer(self, *messages: MessageDocument) -> None:
        for message in messages:
            self.messages.upsert(str(message.id), message)

    def record(self) -> int:
        report = RecordServiceLevelsUseCase(
            self.slot_repo, self.hour_repo, self.source_repo, self.clock.wall_clock
        ).run(TICK)
        return int(report.processed_count)
