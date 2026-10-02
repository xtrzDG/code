from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.job_store_factory import (
    build_periodic_job_run_store_adapter,
    build_queued_job_claim_adapter,
)
from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.jobs import (
    PeriodicJobRunStoreAdapterContract,
    QueuedJobClaimAdapterContract,
)
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.bookings import (
    BookingDocument,
    LeadDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.compliance import (
    AuditLogEntryDocument,
    DpaAcceptanceDocument,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.jobs import (
    PeriodicJobRunDocument,
    QueuedJobDocument,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import (
    ResourceDocument,
    ScheduleExceptionDocument,
)
from app.schemas.domain.users import (
    OtpChallengeDocument,
    UserDocument,
    UserSessionDocument,
)


class DocumentCollectionsContainer(containers.DeclarativeContainer):
    """
    Document collections: Postgres with DATABASE_URL, else in memory.

    Names match app/utilities/storage/document_collection_catalog.py and the
    tables created by migrations/. Every collection is a singleton shared by
    the repositories built on it.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    user_collection = document_collection(
        UserDocument, "users", config, clients, utilities, time_provider
    )
    otp_challenge_collection = document_collection(
        OtpChallengeDocument,
        "otp_challenges",
        config,
        clients,
        utilities,
        time_provider,
    )
    user_session_collection = document_collection(
        UserSessionDocument, "user_sessions", config, clients, utilities, time_provider
    )
    business_collection = document_collection(
        BusinessDocument, "businesses", config, clients, utilities, time_provider
    )
    business_profile_collection = document_collection(
        BusinessProfileDocument,
        "business_profiles",
        config,
        clients,
        utilities,
        time_provider,
    )
    channel_collection = document_collection(
        ChannelDocument, "channels", config, clients, utilities, time_provider
    )
    knowledge_item_collection = document_collection(
        KnowledgeItemDocument,
        "knowledge_items",
        config,
        clients,
        utilities,
        time_provider,
    )
    resource_collection = document_collection(
        ResourceDocument, "resources", config, clients, utilities, time_provider
    )
    schedule_exception_collection = document_collection(
        ScheduleExceptionDocument,
        "schedule_exceptions",
        config,
        clients,
        utilities,
        time_provider,
    )
    contact_collection = document_collection(
        ContactDocument, "contacts", config, clients, utilities, time_provider
    )
    conversation_collection = document_collection(
        ConversationDocument, "conversations", config, clients, utilities, time_provider
    )
    message_collection = document_collection(
        MessageDocument, "messages", config, clients, utilities, time_provider
    )
    llm_turn_collection = document_collection(
        LlmTurnDocument, "llm_turns", config, clients, utilities, time_provider
    )
    call_collection = document_collection(
        CallDocument, "calls", config, clients, utilities, time_provider
    )
    booking_collection = document_collection(
        BookingDocument, "bookings", config, clients, utilities, time_provider
    )
    lead_collection = document_collection(
        LeadDocument, "leads", config, clients, utilities, time_provider
    )
    handoff_collection = document_collection(
        HandoffDocument, "handoffs", config, clients, utilities, time_provider
    )
    unanswered_question_collection = document_collection(
        UnansweredQuestionDocument,
        "unanswered_questions",
        config,
        clients,
        utilities,
        time_provider,
    )
    assistant_version_collection = document_collection(
        AssistantVersionDocument,
        "assistant_versions",
        config,
        clients,
        utilities,
        time_provider,
    )
    autotest_run_collection = document_collection(
        AutotestRunDocument, "autotest_runs", config, clients, utilities, time_provider
    )
    subscription_collection = document_collection(
        SubscriptionDocument, "subscriptions", config, clients, utilities, time_provider
    )
    invoice_collection = document_collection(
        InvoiceDocument, "invoices", config, clients, utilities, time_provider
    )
    usage_event_collection = document_collection(
        UsageEventDocument, "usage_events", config, clients, utilities, time_provider
    )
    audit_log_entry_collection = document_collection(
        AuditLogEntryDocument,
        "audit_log_entries",
        config,
        clients,
        utilities,
        time_provider,
    )
    dpa_acceptance_collection = document_collection(
        DpaAcceptanceDocument,
        "dpa_acceptances",
        config,
        clients,
        utilities,
        time_provider,
    )
    queued_job_collection = document_collection(
        QueuedJobDocument, "queued_jobs", config, clients, utilities, time_provider
    )
    periodic_job_run_collection = document_collection(
        PeriodicJobRunDocument,
        "periodic_job_runs",
        config,
        clients,
        utilities,
        time_provider,
    )
    # Leased job claims and periodic runs (Postgres, or in-process twins).
    queued_job_claims: Singleton[QueuedJobClaimAdapterContract] = Singleton(
        build_queued_job_claim_adapter,
        collection=queued_job_collection,
        connection_pool=clients.postgres_pool,
    )
    periodic_job_run_store: Singleton[PeriodicJobRunStoreAdapterContract] = Singleton(
        build_periodic_job_run_store_adapter,
        collection=periodic_job_run_collection,
        connection_pool=clients.postgres_pool,
    )
    channel_message_receipt_collection = document_collection(
        ChannelMessageReceiptDocument,
        "channel_message_receipts",
        config,
        clients,
        utilities,
        time_provider,
    )
    manager_telegram_link_collection = document_collection(
        ManagerTelegramLinkDocument,
        "manager_telegram_links",
        config,
        clients,
        utilities,
        time_provider,
    )
    # The inbox of webhook messages and the outbox of replies and staff
    # notifications (1020).
    inbound_event_collection = document_collection(
        InboundEventDocument,
        "inbound_events",
        config,
        clients,
        utilities,
        time_provider,
    )
    outbound_message_collection = document_collection(
        OutboundMessageDocument,
        "outbound_messages",
        config,
        clients,
        utilities,
        time_provider,
    )
    calendar_connection_collection = document_collection(
        CalendarConnectionDocument,
        "calendar_connections",
        config,
        clients,
        utilities,
        time_provider,
    )
    calendar_authorization_state_collection = document_collection(
        CalendarAuthorizationStateDocument,
        "calendar_authorization_states",
        config,
        clients,
        utilities,
        time_provider,
    )
    calendar_event_link_collection = document_collection(
        CalendarEventLinkDocument,
        "calendar_event_links",
        config,
        clients,
        utilities,
        time_provider,
    )
    payment_order_collection = document_collection(
        PaymentOrderDocument,
        "payment_orders",
        config,
        clients,
        utilities,
        time_provider,
    )
    package_usage_warning_collection = document_collection(
        PackageUsageWarningDocument,
        "package_usage_warnings",
        config,
        clients,
        utilities,
        time_provider,
    )
