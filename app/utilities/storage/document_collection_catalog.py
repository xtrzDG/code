"""
Collection (table) names of every stored document type: one source of truth
for the container wiring and the migrations (a test checks that both match).
"""

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
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import AuditLogEntryDocument, DpaAcceptanceDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.exchange_rates import ExchangeRateDocument
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.inbox_settings import InboxSettingsDocument
from app.schemas.domain.jobs import (
    PeriodicJobRunDocument,
    QueuedJobDocument,
    WorkerHeartbeatDocument,
)
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.domain.notification_preferences import (
    UserNotificationPreferencesDocument,
)
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.public_slugs import PublicSlugClaimDocument
from app.schemas.domain.push_subscriptions import PushSubscriptionDocument
from app.schemas.domain.quick_replies import QuickReplyLibraryDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.setup import (
    ActivationEventDocument,
    AssistantApplyDocument,
    SetupStateDocument,
)
from app.schemas.domain.staff_deliveries import StaffDeliveryStateDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.schemas.domain.web_vitals import WebVitalSampleDocument
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.access_collections import ACCESS_COLLECTIONS
from app.utilities.storage.activation_collections import ACTIVATION_COLLECTIONS
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.operations_collections import OPERATIONS_COLLECTIONS
from app.utilities.storage.privacy_collections import PRIVACY_COLLECTIONS
from app.utilities.storage.sign_in_document_collections import (
    SIGN_IN_DOCUMENT_COLLECTIONS,
)

DOCUMENT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    # Users and sign-in (platform-wide), two-factor sign-in included.
    *SIGN_IN_DOCUMENT_COLLECTIONS,
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
    # Customers, conversations and the files customers sent (1081).
    DocumentCollectionDefinition(DocumentCollectionName("contacts"), ContactDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("conversations"), ConversationDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("messages"), MessageDocument),
    DocumentCollectionDefinition(DocumentCollectionName("llm_turns"), LlmTurnDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("message_media"), MessageMediaDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("calls"), CallDocument),
    # Bookings, leads, handoffs and open questions.
    DocumentCollectionDefinition(DocumentCollectionName("bookings"), BookingDocument),
    DocumentCollectionDefinition(DocumentCollectionName("leads"), LeadDocument),
    DocumentCollectionDefinition(DocumentCollectionName("handoffs"), HandoffDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("unanswered_questions"), UnansweredQuestionDocument
    ),
    # The team inbox: internal notes on conversations, each business's saved
    # replies and its auto-assignment settings (1053).
    DocumentCollectionDefinition(
        DocumentCollectionName("conversation_notes"), ConversationNoteDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("quick_reply_libraries"), QuickReplyLibraryDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("inbox_settings"), InboxSettingsDocument
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
    # Background work; periodic job runs per period (1011).
    DocumentCollectionDefinition(
        DocumentCollectionName("queued_jobs"), QueuedJobDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("periodic_job_runs"), PeriodicJobRunDocument
    ),
    # The pulse of each worker process, reported by GET /readyz (1030).
    DocumentCollectionDefinition(
        DocumentCollectionName("worker_heartbeats"), WorkerHeartbeatDocument
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
    # Message delivery: the inbox of webhook messages and the outbox of
    # replies and staff notifications (1020).
    DocumentCollectionDefinition(
        DocumentCollectionName("inbound_events"), InboundEventDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("outbound_messages"), OutboundMessageDocument
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
    # Staff notifications: devices that receive them (Web Push), each
    # user's preferences, how delivery to each staff contact went (1043).
    DocumentCollectionDefinition(
        DocumentCollectionName("push_subscriptions"), PushSubscriptionDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("notification_preferences"),
        UserNotificationPreferencesDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("staff_delivery_states"), StaffDeliveryStateDocument
    ),
    # The guided launch: milestones, skipped setup steps and the current
    # "Apply changes" of each business (1044).
    DocumentCollectionDefinition(
        DocumentCollectionName("activation_events"), ActivationEventDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("setup_states"), SetupStateDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("assistant_applies"), AssistantApplyDocument
    ),
    # Missed calls with their text-backs, and call settings (1051).
    DocumentCollectionDefinition(
        DocumentCollectionName("missed_calls"), MissedCallDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("call_settings"), CallSettingsDocument
    ),
    # The hosted chat addresses (/c/{slug}) each business took (1052).
    DocumentCollectionDefinition(
        DocumentCollectionName("public_slug_claims"), PublicSlugClaimDocument
    ),
    # The current knowledge import from each business's website (1054).
    DocumentCollectionDefinition(
        DocumentCollectionName("website_imports"), WebsiteImportDocument
    ),
    # What the assistant is worth: the average check, each owner's digest
    # choices, the stored digests and monthly reports (1061).
    DocumentCollectionDefinition(
        DocumentCollectionName("value_settings"), ValueSettingsDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("digest_preferences"), DigestPreferencesDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("value_reports"), ValueReportDocument
    ),
    # What customers ask about, grouped every night (1100).
    DocumentCollectionDefinition(
        DocumentCollectionName("conversation_topics"), ConversationTopicsDocument
    ),
    # Feedback after visits: review settings, the request per visit (1062).
    DocumentCollectionDefinition(
        DocumentCollectionName("review_settings"), ReviewSettingsDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("feedback_requests"), FeedbackRequestDocument
    ),
    # Key management: the latest re-encryption of the stored secrets (1063).
    DocumentCollectionDefinition(
        DocumentCollectionName("key_rotations"), KeyRotationDocument
    ),
    # Dated exchange rates of the NBG and ECB feeds (1071).
    DocumentCollectionDefinition(
        DocumentCollectionName("exchange_rates"), ExchangeRateDocument
    ),
    # Growth analytics: owners' steps to paying, Web Vitals (1074).
    DocumentCollectionDefinition(
        DocumentCollectionName("product_events"), ProductEventDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("web_vital_samples"), WebVitalSampleDocument
    ),
    # Activation follow-up: nudges sent, done-for-you setup requests (1080).
    *ACTIVATION_COLLECTIONS,
    # Alerts, backups and incidents of the platform itself (1093).
    *OPERATIONS_COLLECTIONS,
    # Platform admins and support's access (1103); suppression, exports (1113).
    *ACCESS_COLLECTIONS,
    *PRIVACY_COLLECTIONS,
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
