"""The operations world's storage: a movable clock, in-memory repositories, fakes."""

from datetime import datetime

from app.adapters.locks.in_memory_advisory_lock_adapter import (
    InMemoryAdvisoryLockAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.locks.business_lock_registry import BusinessLockRegistry
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
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.domain.billing import SubscriptionDocument, UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
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
        self.booking_repo = BookingRepository(
            InMemoryDocumentCollectionAdapter[BookingDocument](BookingDocument)
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        )
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter[ConversationDocument](
                ConversationDocument
            )
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        self.lead_repo = LeadRepository(
            InMemoryDocumentCollectionAdapter[LeadDocument](LeadDocument)
        )
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        )
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
        self.broadcaster = ManagerBroadcastFacilitator(self.notifier)
        self.calendar_sync = RecordingCalendarSync()
        self.lock_registry = BusinessLockRegistry(InMemoryAdvisoryLockAdapter())
