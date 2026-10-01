"""
Collection (table) names of every stored document type.

One source of truth for the container wiring and the migrations: a test
checks that `migrations/` creates a table for every entry here and that
every collection of `AdaptersContainer` has an entry.
"""

from dataclasses import dataclass

from base_pydantic_schemas import PersistentDocument

from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


@dataclass(frozen=True)
class DocumentCollectionDefinition:
    """A stored document type and the name of its collection."""

    name: DocumentCollectionName
    document_type: type[PersistentDocument]


DOCUMENT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    # Users and sign-in (platform-wide).
    DocumentCollectionDefinition(DocumentCollectionName("users"), UserDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("otp_challenges"), OtpChallengeDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("user_sessions"), UserSessionDocument
    ),
    # Businesses, their profile and channels.
    DocumentCollectionDefinition(
        DocumentCollectionName("businesses"), BusinessDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("business_profiles"), BusinessProfileDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("channels"), ChannelDocument),
    # Knowledge, resources and schedules.
    DocumentCollectionDefinition(
        DocumentCollectionName("knowledge_items"), KnowledgeItemDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("resources"), ResourceDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("schedule_exceptions"), ScheduleExceptionDocument
    ),
    # Customers and conversations.
    DocumentCollectionDefinition(DocumentCollectionName("contacts"), ContactDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("conversations"), ConversationDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("messages"), MessageDocument),
    DocumentCollectionDefinition(DocumentCollectionName("llm_turns"), LlmTurnDocument),
    DocumentCollectionDefinition(DocumentCollectionName("calls"), CallDocument),
    # Bookings, leads, handoffs and open questions.
    DocumentCollectionDefinition(DocumentCollectionName("bookings"), BookingDocument),
    DocumentCollectionDefinition(DocumentCollectionName("leads"), LeadDocument),
    DocumentCollectionDefinition(DocumentCollectionName("handoffs"), HandoffDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("unanswered_questions"), UnansweredQuestionDocument
    ),
    # Assistant versions and autotests.
    DocumentCollectionDefinition(
        DocumentCollectionName("assistant_versions"), AssistantVersionDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("autotest_runs"), AutotestRunDocument
    ),
    # Billing and usage.
    DocumentCollectionDefinition(
        DocumentCollectionName("subscriptions"), SubscriptionDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("invoices"), InvoiceDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("usage_events"), UsageEventDocument
    ),
    # Compliance.
    DocumentCollectionDefinition(
        DocumentCollectionName("audit_log_entries"), AuditLogEntryDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("dpa_acceptances"), DpaAcceptanceDocument
    ),
    # Background work.
    DocumentCollectionDefinition(
        DocumentCollectionName("queued_jobs"), QueuedJobDocument
    ),
    # Channels: webhook redelivery receipts and staff Telegram links (0002).
    DocumentCollectionDefinition(
        DocumentCollectionName("channel_message_receipts"),
        ChannelMessageReceiptDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("manager_telegram_links"),
        ManagerTelegramLinkDocument,
    ),
    # Google Calendar: connection, OAuth state, event per booking (0002).
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_connections"), CalendarConnectionDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_authorization_states"),
        CalendarAuthorizationStateDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_event_links"), CalendarEventLinkDocument
    ),
    # Payments: checkout orders and package usage warnings (0003).
    DocumentCollectionDefinition(
        DocumentCollectionName("payment_orders"), PaymentOrderDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("package_usage_warnings"),
        PackageUsageWarningDocument,
    ),
)


def collection_name_for(
    document_type: type[PersistentDocument],
) -> DocumentCollectionName:
    """The catalog name of a document type; NotFoundError when it has none."""

    for definition in DOCUMENT_COLLECTIONS:
        if definition.document_type is document_type:
            return definition.name

    raise NotFoundError(
        f"{document_type.__name__} has no document collection in the catalog."
    )
