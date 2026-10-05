"""
The retention purge over one storage (in memory or Postgres): its
repositories, fake processors and storages, a clock the test moves, and a
seeded history of a customer's conversation at a chosen moment.
"""

from dataclasses import dataclass, field

from typed_time_provider import Microseconds, WallClock

from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.call_follow_up_repositories import MissedCallRepository
from app.repositories.call_repository import CallRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.inbox_repositories import ConversationNoteRepository
from app.repositories.message_media_repository import MessageMediaRepository
from app.repositories.retention_record_repositories import (
    ExpiredLlmTurnRepository,
    ExpiredMessageRepository,
    ExpiredMissedCallRepository,
    ExpiringBookingRepository,
    ExpiringHandoffRepository,
    ExpiringLeadRepository,
    QuietConversationRepository,
)
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
    RetentionPurgeStateRepository,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.compliance.retention.purge_expired_personal_data_use_case import (
    PurgeExpiredPersonalDataUseCase,
)
from tests.media.media_fakes import InMemoryMediaStorage
from tests.privacy.processor_erasure_doubles import ProcessorErasureBed
from tests.storage.builders import COUNTRY_SAMPLES, build_business
from tests.storage.conftest import CollectionFactory
from tests.storage.retention_seeds import SeededHistory, seed_history
from tests.users.accounts_recorders import InMemoryRecordingStorage

DAY_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000
START_MICROSECONDS: int = 1_790_000_000_000_000


@dataclass
class MovableClock:
    """A wall clock at `now`, which the test moves forward."""

    now: int = START_MICROSECONDS

    def wall_clock(self) -> WallClock[Microseconds]:
        return WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: self.now * 1_000,
        )

    def days_ago(self, days: float) -> Microseconds:
        return Microseconds(self.now - int(days * DAY_MICROSECONDS))


@dataclass
class RetentionWorld:
    collections: CollectionFactory
    clock: MovableClock = field(default_factory=MovableClock)
    processors: ProcessorErasureBed = field(default_factory=ProcessorErasureBed)
    recordings: InMemoryRecordingStorage = field(
        default_factory=InMemoryRecordingStorage
    )
    media_storage: InMemoryMediaStorage = field(default_factory=InMemoryMediaStorage)

    def __post_init__(self) -> None:
        build = self.collections
        self.businesses = BusinessRepository(build(BusinessDocument, "businesses"))
        conversation_collection = build(ConversationDocument, "conversations")
        message_collection = build(MessageDocument, "messages")
        turn_collection = build(LlmTurnDocument, "llm_turns")
        lead_collection = build(LeadDocument, "leads")
        booking_collection = build(BookingDocument, "bookings")
        handoff_collection = build(HandoffDocument, "handoffs")
        missed_call_collection = build(MissedCallDocument, "missed_calls")
        self.conversations = ConversationRepository(conversation_collection)
        self.messages = MessageRepository(message_collection)
        self.turns = LlmTurnRepository(turn_collection)
        self.notes = ConversationNoteRepository(
            build(ConversationNoteDocument, "conversation_notes")
        )
        self.calls = CallRepository(build(CallDocument, "calls"))
        self.leads = LeadRepository(lead_collection)
        self.bookings = BookingRepository(booking_collection)
        self.handoffs = HandoffRepository(handoff_collection)
        self.missed_calls = MissedCallRepository(missed_call_collection)
        self.media = MessageMediaRepository(
            build(MessageMediaDocument, "message_media")
        )
        self.audit = AuditLogRepository(
            build(AuditLogEntryDocument, "audit_log_entries")
        )
        self.settings = BusinessPrivacySettingsRepository(
            build(BusinessPrivacySettingsDocument, "business_privacy_settings")
        )
        self.quiet_conversations = QuietConversationRepository(conversation_collection)
        self.expiring_leads = ExpiringLeadRepository(lead_collection)
        self.expiring_bookings = ExpiringBookingRepository(booking_collection)
        self.states = RetentionPurgeStateRepository(
            build(RetentionPurgeStateDocument, "retention_purge_states")
        )
        self.purge = PurgeExpiredPersonalDataUseCase(
            business_repo=self.businesses,
            privacy_settings_repo=self.settings,
            purge_state_repo=self.states,
            quiet_conversation_repo=self.quiet_conversations,
            llm_turn_repo=ExpiredLlmTurnRepository(turn_collection),
            note_repo=self.notes,
            call_repo=self.calls,
            recording_storage=self.recordings,
            message_repo=ExpiredMessageRepository(message_collection),
            message_media_repo=self.media,
            media_storage=self.media_storage,
            missed_call_repo=ExpiredMissedCallRepository(missed_call_collection),
            lead_repo=self.expiring_leads,
            booking_repo=self.expiring_bookings,
            handoff_repo=ExpiringHandoffRepository(handoff_collection),
            processor_erasure=self.processors.facilitator(),
            audit_log_repo=self.audit,
            wall_clock=self.clock.wall_clock(),
        )

    def new_business(self) -> BusinessDocument:
        business = build_business(COUNTRY_SAMPLES[0], UserId())
        self.businesses.save(business)
        return business

    def history(self, business: BusinessDocument, days_ago: float) -> SeededHistory:
        """A conversation (and all that hangs on it) quiet for `days_ago`."""

        return seed_history(self, business, self.clock.days_ago(days_ago))

    def retention_entries(self, business: BusinessDocument) -> dict[str, int]:
        """The RETENTION_PURGE counts of the business's log, by entity."""

        counts: dict[str, int] = {}
        for entry in self.audit.list_by_business(business.id):
            if entry.action.value == "retention_purge":
                counts[str(entry.entity)] = counts.get(str(entry.entity), 0) + int(
                    entry.record_count or 0
                )

        return counts
