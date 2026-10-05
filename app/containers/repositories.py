from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.notification_collections_container import (
    NotificationCollectionsContainer,
)
from app.containers.analytics_repositories import AnalyticsRepositoriesContainer
from app.containers.billing_repositories import BillingRepositoriesContainer
from app.containers.call_repositories import CallRepositoriesContainer
from app.containers.client_care_repositories import ClientCareRepositoriesContainer
from app.containers.feedback_repositories import FeedbackRepositoriesContainer
from app.containers.inbox_repositories import InboxRepositoriesContainer
from app.containers.launch_repositories import LaunchRepositoriesContainer
from app.containers.legal_repositories import LegalRepositoriesContainer
from app.containers.media_repositories import MediaRepositoriesContainer
from app.containers.operations_repositories import OperationsRepositoriesContainer
from app.containers.privacy_repositories import PrivacyRepositoriesContainer
from app.containers.rate_repositories import RateRepositoriesContainer
from app.containers.retention_repositories import RetentionRepositoriesContainer
from app.containers.security_repositories import SecurityRepositoriesContainer
from app.containers.value_repositories import ValueRepositoriesContainer
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
from app.repositories.attention_count_repository import AttentionCountRepository
from app.repositories.billing_repositories import (
    InvoiceRepository,
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
    ChannelRepository,
)
from app.repositories.calendar_repositories import (
    CalendarAuthorizationStateRepository,
    CalendarConnectionRepository,
    CalendarEventLinkRepository,
)
from app.repositories.call_repository import CallRepository
from app.repositories.channel_repositories import (
    ChannelMessageReceiptRepository,
    ManagerTelegramLinkRepository,
)
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.contact_activity_repository import ContactActivityRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.delivery_repositories import (
    InboundEventRepository,
    OutboundMessageRepository,
)
from app.repositories.inbox_work_repository import InboxWorkRepository
from app.repositories.job_repositories import (
    PeriodicJobRunRepository,
    QueuedJobRepository,
)
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.notification_repositories import (
    NotificationPreferencesRepository,
    PushSubscriptionRepository,
    StaffDeliveryStateRepository,
)
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)
from app.repositories.value_count_repository import ValueCountRepository
from app.repositories.worker_heartbeat_repository import WorkerHeartbeatRepository


class RepositoriesContainer(
    CallRepositoriesContainer,
    InboxRepositoriesContainer,
    LaunchRepositoriesContainer,
    SecurityRepositoriesContainer,
    ValueRepositoriesContainer,
    FeedbackRepositoriesContainer,
    RateRepositoriesContainer,
    AnalyticsRepositoriesContainer,
    MediaRepositoriesContainer,
    OperationsRepositoriesContainer,
    PrivacyRepositoriesContainer,
    RetentionRepositoriesContainer,
    BillingRepositoriesContainer,
    LegalRepositoriesContainer,
    ClientCareRepositoriesContainer,
):
    """The repositories (singletons); those of each later module: the bases."""

    collections: DocumentCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]
    notification_collections: NotificationCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    user_repo: Singleton[UserRepository] = Singleton(
        UserRepository,
        collection=collections.user_collection,
    )
    otp_challenge_repo: Singleton[OtpChallengeRepository] = Singleton(
        OtpChallengeRepository,
        collection=collections.otp_challenge_collection,
    )
    user_session_repo: Singleton[UserSessionRepository] = Singleton(
        UserSessionRepository,
        collection=collections.user_session_collection,
    )
    business_repo: Singleton[BusinessRepository] = Singleton(
        BusinessRepository,
        collection=collections.business_collection,
    )
    channel_repo: Singleton[ChannelRepository] = Singleton(
        ChannelRepository,
        collection=collections.channel_collection,
    )
    business_profile_repo: Singleton[BusinessProfileRepository] = Singleton(
        BusinessProfileRepository,
        collection=collections.business_profile_collection,
    )
    knowledge_item_repo: Singleton[KnowledgeItemRepository] = Singleton(
        KnowledgeItemRepository,
        collection=collections.knowledge_item_collection,
    )
    resource_repo: Singleton[ResourceRepository] = Singleton(
        ResourceRepository,
        collection=collections.resource_collection,
    )
    schedule_exception_repo: Singleton[ScheduleExceptionRepository] = Singleton(
        ScheduleExceptionRepository,
        collection=collections.schedule_exception_collection,
    )
    contact_repo: Singleton[ContactRepository] = Singleton(
        ContactRepository,
        collection=collections.contact_collection,
    )
    contact_activity_repo: Singleton[ContactActivityRepository] = Singleton(
        ContactActivityRepository,
        conversation_collection=collections.conversation_collection,
        booking_collection=collections.booking_collection,
        lead_collection=collections.lead_collection,
    )
    conversation_repo: Singleton[ConversationRepository] = Singleton(
        ConversationRepository,
        collection=collections.conversation_collection,
    )
    message_repo: Singleton[MessageRepository] = Singleton(
        MessageRepository,
        collection=collections.message_collection,
    )
    llm_turn_repo: Singleton[LlmTurnRepository] = Singleton(
        LlmTurnRepository,
        collection=collections.llm_turn_collection,
    )
    call_repo: Singleton[CallRepository] = Singleton(
        CallRepository,
        collection=collections.call_collection,
    )
    booking_repo: Singleton[BookingRepository] = Singleton(
        BookingRepository,
        collection=collections.booking_collection,
    )
    lead_repo: Singleton[LeadRepository] = Singleton(
        LeadRepository,
        collection=collections.lead_collection,
    )
    inbox_work_repo: Singleton[InboxWorkRepository] = Singleton(
        InboxWorkRepository,
        handoff_collection=collections.handoff_collection,
        lead_collection=collections.lead_collection,
    )
    handoff_repo: Singleton[HandoffRepository] = Singleton(
        HandoffRepository,
        collection=collections.handoff_collection,
    )
    # Indexed counts of what waits for a person (navigation badges).
    attention_count_repo: Singleton[AttentionCountRepository] = Singleton(
        AttentionCountRepository,
        booking_collection=collections.booking_collection,
        channel_collection=collections.channel_collection,
    )
    # Counts of the value model beyond the dashboard's (1061).
    value_count_repo: Singleton[ValueCountRepository] = Singleton(
        ValueCountRepository,
        booking_collection=collections.booking_collection,
        message_collection=collections.message_collection,
    )
    unanswered_question_repo: Singleton[UnansweredQuestionRepository] = Singleton(
        UnansweredQuestionRepository,
        collection=collections.unanswered_question_collection,
    )
    assistant_version_repo: Singleton[AssistantVersionRepository] = Singleton(
        AssistantVersionRepository,
        collection=collections.assistant_version_collection,
    )
    autotest_run_repo: Singleton[AutotestRunRepository] = Singleton(
        AutotestRunRepository,
        collection=collections.autotest_run_collection,
    )
    subscription_repo: Singleton[SubscriptionRepository] = Singleton(
        SubscriptionRepository,
        collection=collections.subscription_collection,
    )
    invoice_repo: Singleton[InvoiceRepository] = Singleton(
        InvoiceRepository,
        collection=collections.invoice_collection,
    )
    usage_event_repo: Singleton[UsageEventRepository] = Singleton(
        UsageEventRepository,
        collection=collections.usage_event_collection,
    )
    audit_log_repo: Singleton[AuditLogRepository] = Singleton(
        AuditLogRepository,
        collection=collections.audit_log_entry_collection,
    )
    dpa_acceptance_repo: Singleton[DpaAcceptanceRepository] = Singleton(
        DpaAcceptanceRepository,
        collection=collections.dpa_acceptance_collection,
    )
    queued_job_repo: Singleton[QueuedJobRepository] = Singleton(
        QueuedJobRepository,
        collection=collections.queued_job_collection,
        claims=collections.queued_job_claims,
    )
    periodic_job_run_repo: Singleton[PeriodicJobRunRepository] = Singleton(
        PeriodicJobRunRepository,
        store=collections.periodic_job_run_store,
    )
    worker_heartbeat_repo: Singleton[WorkerHeartbeatRepository] = Singleton(
        WorkerHeartbeatRepository,
        collection=collections.worker_heartbeat_collection,
    )
    channel_message_receipt_repo: Singleton[ChannelMessageReceiptRepository] = (
        Singleton(
            ChannelMessageReceiptRepository,
            collection=collections.channel_message_receipt_collection,
        )
    )
    inbound_event_repo: Singleton[InboundEventRepository] = Singleton(
        InboundEventRepository,
        collection=collections.inbound_event_collection,
    )
    outbound_message_repo: Singleton[OutboundMessageRepository] = Singleton(
        OutboundMessageRepository,
        collection=collections.outbound_message_collection,
    )
    manager_telegram_link_repo: Singleton[ManagerTelegramLinkRepository] = Singleton(
        ManagerTelegramLinkRepository,
        collection=collections.manager_telegram_link_collection,
    )
    calendar_connection_repo: Singleton[CalendarConnectionRepository] = Singleton(
        CalendarConnectionRepository,
        collection=collections.calendar_connection_collection,
    )
    calendar_authorization_state_repo: Singleton[
        CalendarAuthorizationStateRepository
    ] = Singleton(
        CalendarAuthorizationStateRepository,
        collection=collections.calendar_authorization_state_collection,
    )
    calendar_event_link_repo: Singleton[CalendarEventLinkRepository] = Singleton(
        CalendarEventLinkRepository,
        collection=collections.calendar_event_link_collection,
    )
    # Staff notifications: devices (Web Push), preferences, delivery states.
    push_subscription_repo: Singleton[PushSubscriptionRepository] = Singleton(
        PushSubscriptionRepository,
        collection=notification_collections.push_subscription_collection,
    )
    notification_preferences_repo: Singleton[NotificationPreferencesRepository] = (
        Singleton(
            NotificationPreferencesRepository,
            collection=notification_collections.notification_preferences_collection,
        )
    )
    staff_delivery_state_repo: Singleton[StaffDeliveryStateRepository] = Singleton(
        StaffDeliveryStateRepository,
        collection=notification_collections.staff_delivery_state_collection,
    )
