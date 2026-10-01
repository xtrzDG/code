from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters import AdaptersContainer
from app.repositories.assistant_repositories import (
    AssistantVersionRepository,
    AutotestRunRepository,
)
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
from app.repositories.channel_repositories import (
    ChannelMessageReceiptRepository,
    ManagerTelegramLinkRepository,
)
from app.repositories.compliance_repositories import (
    AuditLogRepository,
    DpaAcceptanceRepository,
)
from app.repositories.conversation_repositories import (
    CallRepository,
    ContactRepository,
    ConversationRepository,
    LlmTurnRepository,
    MessageRepository,
)
from app.repositories.job_repositories import QueuedJobRepository
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.payment_repositories import (
    PackageUsageWarningRepository,
    PaymentOrderRepository,
)
from app.repositories.user_repositories import (
    OtpChallengeRepository,
    UserRepository,
    UserSessionRepository,
)


class RepositoriesContainer(containers.DeclarativeContainer):
    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]

    user_repo: Singleton[UserRepository] = Singleton(
        UserRepository,
        collection=adapters.user_collection,
    )
    otp_challenge_repo: Singleton[OtpChallengeRepository] = Singleton(
        OtpChallengeRepository,
        collection=adapters.otp_challenge_collection,
    )
    user_session_repo: Singleton[UserSessionRepository] = Singleton(
        UserSessionRepository,
        collection=adapters.user_session_collection,
    )
    business_repo: Singleton[BusinessRepository] = Singleton(
        BusinessRepository,
        collection=adapters.business_collection,
    )
    channel_repo: Singleton[ChannelRepository] = Singleton(
        ChannelRepository,
        collection=adapters.channel_collection,
    )
    business_profile_repo: Singleton[BusinessProfileRepository] = Singleton(
        BusinessProfileRepository,
        collection=adapters.business_profile_collection,
    )
    knowledge_item_repo: Singleton[KnowledgeItemRepository] = Singleton(
        KnowledgeItemRepository,
        collection=adapters.knowledge_item_collection,
    )
    resource_repo: Singleton[ResourceRepository] = Singleton(
        ResourceRepository,
        collection=adapters.resource_collection,
    )
    schedule_exception_repo: Singleton[ScheduleExceptionRepository] = Singleton(
        ScheduleExceptionRepository,
        collection=adapters.schedule_exception_collection,
    )
    contact_repo: Singleton[ContactRepository] = Singleton(
        ContactRepository,
        collection=adapters.contact_collection,
    )
    conversation_repo: Singleton[ConversationRepository] = Singleton(
        ConversationRepository,
        collection=adapters.conversation_collection,
    )
    message_repo: Singleton[MessageRepository] = Singleton(
        MessageRepository,
        collection=adapters.message_collection,
    )
    llm_turn_repo: Singleton[LlmTurnRepository] = Singleton(
        LlmTurnRepository,
        collection=adapters.llm_turn_collection,
    )
    call_repo: Singleton[CallRepository] = Singleton(
        CallRepository,
        collection=adapters.call_collection,
    )
    booking_repo: Singleton[BookingRepository] = Singleton(
        BookingRepository,
        collection=adapters.booking_collection,
    )
    lead_repo: Singleton[LeadRepository] = Singleton(
        LeadRepository,
        collection=adapters.lead_collection,
    )
    handoff_repo: Singleton[HandoffRepository] = Singleton(
        HandoffRepository,
        collection=adapters.handoff_collection,
    )
    unanswered_question_repo: Singleton[UnansweredQuestionRepository] = Singleton(
        UnansweredQuestionRepository,
        collection=adapters.unanswered_question_collection,
    )
    assistant_version_repo: Singleton[AssistantVersionRepository] = Singleton(
        AssistantVersionRepository,
        collection=adapters.assistant_version_collection,
    )
    autotest_run_repo: Singleton[AutotestRunRepository] = Singleton(
        AutotestRunRepository,
        collection=adapters.autotest_run_collection,
    )
    subscription_repo: Singleton[SubscriptionRepository] = Singleton(
        SubscriptionRepository,
        collection=adapters.subscription_collection,
    )
    invoice_repo: Singleton[InvoiceRepository] = Singleton(
        InvoiceRepository,
        collection=adapters.invoice_collection,
    )
    usage_event_repo: Singleton[UsageEventRepository] = Singleton(
        UsageEventRepository,
        collection=adapters.usage_event_collection,
    )
    audit_log_repo: Singleton[AuditLogRepository] = Singleton(
        AuditLogRepository,
        collection=adapters.audit_log_entry_collection,
    )
    dpa_acceptance_repo: Singleton[DpaAcceptanceRepository] = Singleton(
        DpaAcceptanceRepository,
        collection=adapters.dpa_acceptance_collection,
    )
    queued_job_repo: Singleton[QueuedJobRepository] = Singleton(
        QueuedJobRepository,
        collection=adapters.queued_job_collection,
    )
    channel_message_receipt_repo: Singleton[ChannelMessageReceiptRepository] = (
        Singleton(
            ChannelMessageReceiptRepository,
            collection=adapters.channel_message_receipt_collection,
        )
    )
    manager_telegram_link_repo: Singleton[ManagerTelegramLinkRepository] = Singleton(
        ManagerTelegramLinkRepository,
        collection=adapters.manager_telegram_link_collection,
    )
    calendar_connection_repo: Singleton[CalendarConnectionRepository] = Singleton(
        CalendarConnectionRepository,
        collection=adapters.calendar_connection_collection,
    )
    calendar_authorization_state_repo: Singleton[
        CalendarAuthorizationStateRepository
    ] = Singleton(
        CalendarAuthorizationStateRepository,
        collection=adapters.calendar_authorization_state_collection,
    )
    calendar_event_link_repo: Singleton[CalendarEventLinkRepository] = Singleton(
        CalendarEventLinkRepository,
        collection=adapters.calendar_event_link_collection,
    )
    payment_order_repo: Singleton[PaymentOrderRepository] = Singleton(
        PaymentOrderRepository,
        collection=adapters.payment_order_collection,
    )
    package_usage_warning_repo: Singleton[PackageUsageWarningRepository] = Singleton(
        PackageUsageWarningRepository,
        collection=adapters.package_usage_warning_collection,
    )
