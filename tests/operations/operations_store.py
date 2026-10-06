"""The operations world's storage: a movable clock, in-memory repositories, fakes."""

from datetime import datetime

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.growth.growth_bookings_facilitator import (
    GrowthBookingsFacilitator,
)
from app.facilitators.notifications.staff_alert_facilitator import (
    StaffAlertFacilitator,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.repositories.attention_count_repository import AttentionCountRepository
from app.repositories.billing_repositories import (
    SubscriptionRepository,
    UsageEventRepository,
)
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
    UnansweredQuestionRepository,
)
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.repositories.campaign_repositories import CampaignMessageRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.inbox_repositories import InboxSettingsRepository
from app.repositories.inbox_work_repository import InboxWorkRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.setup_repositories import ActivationEventRepository
from app.repositories.user_repositories import UserRepository
from app.repositories.waitlist_repositories import (
    WaitlistEntryRepository,
    WaitlistSettingsRepository,
)
from app.schemas.domain.billing import SubscriptionDocument, UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from tests.channels.outbox_fakes import RecordingJobQueue
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.notifications.staff_alert_fakes import RecordingPushQueue, build_staff_alerts
from tests.operations.builders import DEFAULT_NOW
from tests.operations.fakes import (
    FakeLocalizedTextResolver,
    MovableClock,
    PhonenumbersParser,
    RecordingCalendarSync,
    RecordingManagerNotifier,
)


class OperationsStore:
    """Repositories, clock and recording fakes the operations use cases share."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        self.clock = MovableClock(now)
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.profile_repo = BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
                BusinessProfileDocument
            )
        )
        self.resource_repo = ResourceRepository(
            InMemoryDocumentCollectionAdapter[ResourceDocument](ResourceDocument)
        )
        self.exception_repo = ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument](
                ScheduleExceptionDocument
            )
        )
        self.booking_collection = InMemoryDocumentCollectionAdapter[BookingDocument](
            BookingDocument
        )
        self.booking_repo = BookingRepository(self.booking_collection)
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        )
        self.conversation_collection = InMemoryDocumentCollectionAdapter[
            ConversationDocument
        ](ConversationDocument)
        self.conversation_repo = ConversationRepository(self.conversation_collection)
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        lead_collection = InMemoryDocumentCollectionAdapter[LeadDocument](LeadDocument)
        self.lead_collection = lead_collection
        self.lead_repo = LeadRepository(lead_collection)
        handoff_collection = InMemoryDocumentCollectionAdapter[HandoffDocument](
            HandoffDocument
        )
        self.handoff_repo = HandoffRepository(handoff_collection)
        # The team inbox: open work of conversations, auto-assignment.
        self.inbox_work_repo = InboxWorkRepository(handoff_collection, lead_collection)
        self.inbox_settings_repo = InboxSettingsRepository(
            InMemoryDocumentCollectionAdapter[InboxSettingsDocument](
                InboxSettingsDocument
            )
        )
        self.channel_collection = InMemoryDocumentCollectionAdapter[ChannelDocument](
            ChannelDocument
        )
        self.attention_count_repo = AttentionCountRepository(
            self.booking_collection,
            self.channel_collection,
        )
        self.live_events = RecordingEventPublisher()
        self.question_repo = UnansweredQuestionRepository(
            InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument](
                UnansweredQuestionDocument
            )
        )
        self.knowledge_repo = KnowledgeItemRepository(
            InMemoryDocumentCollectionAdapter[KnowledgeItemDocument](
                KnowledgeItemDocument
            )
        )
        self.usage_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        )
        self.plan_registry = PlanRegistry()
        self.activation_event_repo = ActivationEventRepository(
            InMemoryDocumentCollectionAdapter[ActivationEventDocument](
                ActivationEventDocument
            )
        )
        self.audit_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
                AuditLogEntryDocument
            )
        )
        self.user_repo = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.resolver = FakeLocalizedTextResolver()
        self.phone_parser = PhonenumbersParser()
        self.notifier = RecordingManagerNotifier()
        self.push_queue = RecordingPushQueue()
        self.staff_alerts: StaffAlertFacilitator = self.rebuild_staff_alerts()
        self.calendar_sync = RecordingCalendarSync()
        self.lock_registry = BusinessLockRegistry(InMemoryAdvisoryLockAdapter())
        self.waitlist_entry_repo = WaitlistEntryRepository(
            InMemoryDocumentCollectionAdapter(WaitlistEntryDocument)
        )
        self.waitlist_settings_repo = WaitlistSettingsRepository(
            InMemoryDocumentCollectionAdapter(WaitlistSettingsDocument)
        )
        self.campaign_message_repo = CampaignMessageRepository(
            InMemoryDocumentCollectionAdapter(CampaignMessageDocument)
        )
        self.job_queue = RecordingJobQueue()
        self.growth = GrowthBookingsFacilitator(
            waitlist_entry_repo=self.waitlist_entry_repo,
            waitlist_settings_repo=self.waitlist_settings_repo,
            campaign_message_repo=self.campaign_message_repo,
            job_queue=self.job_queue,
        )

    def rebuild_staff_alerts(self) -> StaffAlertFacilitator:
        """Staff alerts over the current notifier (after replacing it)."""

        self.staff_alerts = build_staff_alerts(
            self.notifier,
            self.resolver,
            self.clock.wall_clock,
            push_queue=self.push_queue,
        )
        return self.staff_alerts
