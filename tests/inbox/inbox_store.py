"""The in-memory storage of the team inbox tests: repositories and a team."""

from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds, WallClock

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.attention_count_repository import AttentionCountRepository
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
)
from app.repositories.business_repositories import BusinessRepository
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.inbox_repositories import (
    ConversationNoteRepository,
    InboxSettingsRepository,
    QuickReplyLibraryRepository,
)
from app.repositories.inbox_work_repository import InboxWorkRepository
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.users import BusinessMemberRole, LoginMethod
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument, BusinessMember
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from tests.live_events.recording_event_publisher import RecordingEventPublisher
from tests.storage.builders import COUNTRY_SAMPLES, build_business

# 2026-10-03T09:00:00Z in UNIX microseconds.
NOW: Microseconds = Microseconds(1_791_018_000_000_000)


def collection[Document: PersistentDocument](
    document_type: type[Document],
) -> InMemoryDocumentCollectionAdapter[Document]:
    return InMemoryDocumentCollectionAdapter[Document](document_type)


def build_user(name: str) -> UserDocument:
    return UserDocument(
        login_method=LoginMethod.EMAIL,
        locale=LanguageTag("en"),
        display_name=UserDisplayName(name),
    )


class InboxStore:
    """
    A Georgian restaurant with its owner Nino and two staff members, Giorgi
    and Ana, a stranger who is no member, and every repository the inbox
    reads, in memory; the clock stands still at NOW until moved.
    """

    def __init__(self) -> None:
        self.now: Microseconds = NOW
        self.wall_clock: WallClock[Microseconds] = WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: int(self.now) * 1_000,
        )
        self.live_events = RecordingEventPublisher()
        self.user_repo = UserRepository(collection(UserDocument))
        self.owner = build_user("Nino")
        self.staff = build_user("Giorgi")
        self.colleague = build_user("Ana")
        self.stranger = build_user("Levan")
        for user in (self.owner, self.staff, self.colleague, self.stranger):
            self.user_repo.save(user)

        business: BusinessDocument = build_business(COUNTRY_SAMPLES[0], self.owner.id)
        business.members = [
            *business.members,
            BusinessMember(user_id=self.staff.id, role=BusinessMemberRole.STAFF),
            BusinessMember(user_id=self.colleague.id, role=BusinessMemberRole.STAFF),
        ]
        self.business_repo = BusinessRepository(collection(BusinessDocument))
        self.business_repo.save(business)
        self.business: BusinessDocument = business
        handoffs = collection(HandoffDocument)
        leads = collection(LeadDocument)
        self.handoff_repo = HandoffRepository(handoffs)
        self.lead_repo = LeadRepository(leads)
        self.inbox_work_repo = InboxWorkRepository(handoffs, leads)
        bookings = collection(BookingDocument)
        self.booking_repo = BookingRepository(bookings)
        self.channel_collection = collection(ChannelDocument)
        self.attention_count_repo = AttentionCountRepository(
            bookings, self.channel_collection
        )
        self.contact_repo = ContactRepository(collection(ContactDocument))
        self.conversation_repo = ConversationRepository(
            collection(ConversationDocument)
        )
        self.message_repo = MessageRepository(collection(MessageDocument))
        self.note_repo = ConversationNoteRepository(
            collection(ConversationNoteDocument)
        )
        self.quick_reply_repo = QuickReplyLibraryRepository(
            collection(QuickReplyLibraryDocument)
        )
        self.settings_repo = InboxSettingsRepository(collection(InboxSettingsDocument))
        self.audit_log_repo = AuditLogRepository(collection(AuditLogEntryDocument))

    def later(self, minutes: int) -> Microseconds:
        """Move the clock on."""

        self.now = Microseconds(int(self.now) + minutes * 60_000_000)
        return self.now

    def audit_entries(self) -> list[AuditLogEntryDocument]:
        return self.audit_log_repo.list_by_business(self.business.id)

    def member_ids(self) -> list[UserId]:
        return [member.user_id for member in self.business.members]
