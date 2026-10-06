from dependency_injector.providers import Container

from app.containers.orchestrators.assistant_orchestrators import (
    AssistantOrchestratorsContainer,
)
from app.containers.orchestrators.billing_orchestrators import (
    BillingOrchestratorsContainer,
)
from app.containers.orchestrators.booking_link_orchestrators import (
    BookingLinkOrchestratorsContainer,
)
from app.containers.orchestrators.calendar_sync_orchestrators import (
    CalendarSyncOrchestratorsContainer,
)
from app.containers.orchestrators.call_orchestrators import (
    CallOrchestratorsContainer,
)
from app.containers.orchestrators.channel_orchestrators import (
    ChannelOrchestratorsContainer,
)
from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
)
from app.containers.orchestrators.core_orchestrators_container import (
    CoreOrchestratorsContainer,
)
from app.containers.orchestrators.customer_orchestrators import (
    CustomerOrchestratorsContainer,
)
from app.containers.orchestrators.feedback_orchestrators import (
    FeedbackOrchestratorsContainer,
)
from app.containers.orchestrators.growth_orchestrators import (
    GrowthOrchestratorsContainer,
)
from app.containers.orchestrators.inbox_orchestrators import (
    InboxOrchestratorsContainer,
)
from app.containers.orchestrators.knowledge_orchestrators import (
    KnowledgeOrchestratorsContainer,
)
from app.containers.orchestrators.memory_orchestrators import (
    MemoryOrchestratorsContainer,
)
from app.containers.orchestrators.notification_orchestrators import (
    NotificationOrchestratorsContainer,
)
from app.containers.orchestrators.operations_orchestrators import (
    OperationsOrchestratorsContainer,
)
from app.containers.orchestrators.setup_orchestrators import (
    SetupOrchestratorsContainer,
)
from app.containers.orchestrators.sharing_orchestrators import (
    SharingOrchestratorsContainer,
)
from app.containers.orchestrators.subscription_lifecycle_orchestrators import (
    SubscriptionLifecycleOrchestratorsContainer,
)
from app.containers.orchestrators.value_orchestrators import (
    ValueOrchestratorsContainer,
)


class OrchestratorsContainer(CoreOrchestratorsContainer):
    """
    Orchestrators, one child container per bounded context: the generic one
    around each single-use-case endpoint and the dedicated ones that
    coordinate several use cases. The edges and the platform's own contexts
    come from `CoreOrchestratorsContainer`; this layer adds a business's own
    work (conversations, calls, assistants, channels, billing, growth).

    The autotest scenario runner is a use case of the assembly module, but it
    drives the conversation turn orchestrator, so it is wired with the
    assistant orchestrators (the use cases container cannot depend on
    orchestrators).
    """

    inbox: InboxOrchestratorsContainer = Container(  # type: ignore[assignment]
        InboxOrchestratorsContainer,
        inbox_use_cases=CoreOrchestratorsContainer.use_cases.inbox,
    )
    memory: MemoryOrchestratorsContainer = Container(  # type: ignore[assignment]
        MemoryOrchestratorsContainer,
        memory_use_cases=CoreOrchestratorsContainer.use_cases.memory,
    )
    customers: CustomerOrchestratorsContainer = Container(  # type: ignore[assignment]
        CustomerOrchestratorsContainer,
        customer_use_cases=CoreOrchestratorsContainer.use_cases.customers,
    )
    knowledge: KnowledgeOrchestratorsContainer = Container(  # type: ignore[assignment]
        KnowledgeOrchestratorsContainer,
        knowledge_use_cases=CoreOrchestratorsContainer.use_cases.knowledge,
        menu_import_use_cases=CoreOrchestratorsContainer.use_cases.menu_import,
        scheduling_use_cases=CoreOrchestratorsContainer.use_cases.scheduling,
    )
    operations: OperationsOrchestratorsContainer = Container(  # type: ignore[assignment]
        OperationsOrchestratorsContainer,
        scheduling_use_cases=CoreOrchestratorsContainer.use_cases.scheduling,
        booking_use_cases=CoreOrchestratorsContainer.use_cases.bookings,
        follow_up_use_cases=CoreOrchestratorsContainer.use_cases.follow_ups,
    )
    calls: CallOrchestratorsContainer = Container(  # type: ignore[assignment]
        CallOrchestratorsContainer,
        call_use_cases=CoreOrchestratorsContainer.use_cases.calls,
    )
    conversations: ConversationOrchestratorsContainer = Container(  # type: ignore[assignment]
        ConversationOrchestratorsContainer,
        utilities=CoreOrchestratorsContainer.utilities,
        account_use_cases=CoreOrchestratorsContainer.use_cases.accounts,
        follow_up_use_cases=CoreOrchestratorsContainer.use_cases.follow_ups,
        conversation_use_cases=CoreOrchestratorsContainer.use_cases.conversations,
        conversation_feed_use_cases=CoreOrchestratorsContainer.use_cases.conversation_feed,
        voice_use_cases=CoreOrchestratorsContainer.use_cases.voice,
        delivery_use_cases=CoreOrchestratorsContainer.use_cases.deliveries,
        call_use_cases=CoreOrchestratorsContainer.use_cases.calls,
        call_orchestrators=calls,
        feedback_use_cases=CoreOrchestratorsContainer.use_cases.feedback,
        spend_guard_use_cases=CoreOrchestratorsContainer.use_cases.spend_guard,
        waitlist_use_cases=CoreOrchestratorsContainer.use_cases.waitlist,
    )
    assistants: AssistantOrchestratorsContainer = Container(  # type: ignore[assignment]
        AssistantOrchestratorsContainer,
        adapters=CoreOrchestratorsContainer.adapters,
        config=CoreOrchestratorsContainer.config,
        repositories=CoreOrchestratorsContainer.repositories,
        assistant_use_cases=CoreOrchestratorsContainer.use_cases.assistants,
        autotest_use_cases=CoreOrchestratorsContainer.use_cases.autotests,
        apply_use_cases=CoreOrchestratorsContainer.use_cases.apply,
        pending_change_use_cases=CoreOrchestratorsContainer.use_cases.pending_changes,
        conversation_orchestrators=conversations,
    )
    setup: SetupOrchestratorsContainer = Container(  # type: ignore[assignment]
        SetupOrchestratorsContainer,
        setup_use_cases=CoreOrchestratorsContainer.use_cases.setup,
        launch_use_cases=CoreOrchestratorsContainer.use_cases.launch,
        guide_use_cases=CoreOrchestratorsContainer.use_cases.guide,
    )
    channels: ChannelOrchestratorsContainer = Container(  # type: ignore[assignment]
        ChannelOrchestratorsContainer,
        channel_use_cases=CoreOrchestratorsContainer.use_cases.channels,
        delivery_use_cases=CoreOrchestratorsContainer.use_cases.deliveries,
        follow_up_use_cases=CoreOrchestratorsContainer.use_cases.follow_ups,
        conversation_use_cases=CoreOrchestratorsContainer.use_cases.conversations,
        reply_speed_use_cases=CoreOrchestratorsContainer.use_cases.reply_speed,
        config=CoreOrchestratorsContainer.config,
        facilitators=CoreOrchestratorsContainer.facilitators,
        time_provider=CoreOrchestratorsContainer.time_provider,
        utilities=CoreOrchestratorsContainer.utilities,
    )
    billing: BillingOrchestratorsContainer = Container(  # type: ignore[assignment]
        BillingOrchestratorsContainer,
        billing_use_cases=CoreOrchestratorsContainer.use_cases.billing,
        invoicing_use_cases=CoreOrchestratorsContainer.use_cases.invoicing,
    )
    notifications: NotificationOrchestratorsContainer = Container(  # type: ignore[assignment]
        NotificationOrchestratorsContainer,
        notification_use_cases=CoreOrchestratorsContainer.use_cases.notifications,
        delivery_use_cases=CoreOrchestratorsContainer.use_cases.deliveries,
    )
    sharing: SharingOrchestratorsContainer = Container(  # type: ignore[assignment]
        SharingOrchestratorsContainer,
        sharing_use_cases=CoreOrchestratorsContainer.use_cases.sharing,
        follow_up_use_cases=CoreOrchestratorsContainer.use_cases.follow_ups,
        utilities=CoreOrchestratorsContainer.utilities,
    )
    booking_links: BookingLinkOrchestratorsContainer = Container(  # type: ignore[assignment]
        BookingLinkOrchestratorsContainer,
        booking_link_use_cases=CoreOrchestratorsContainer.use_cases.booking_links,
        utilities=CoreOrchestratorsContainer.utilities,
    )
    feedback: FeedbackOrchestratorsContainer = Container(  # type: ignore[assignment]
        FeedbackOrchestratorsContainer,
        feedback_use_cases=CoreOrchestratorsContainer.use_cases.feedback,
    )
    # The waitlist and the rebooking campaigns (1151).
    growth: GrowthOrchestratorsContainer = Container(  # type: ignore[assignment]
        GrowthOrchestratorsContainer,
        waitlist_use_cases=CoreOrchestratorsContainer.use_cases.waitlist,
        campaign_use_cases=CoreOrchestratorsContainer.use_cases.campaigns,
    )
    # Cancel reasons, offers, the seasonal pause and win-back (1161).
    lifecycle: SubscriptionLifecycleOrchestratorsContainer = Container(  # type: ignore[assignment]
        SubscriptionLifecycleOrchestratorsContainer,
        lifecycle=CoreOrchestratorsContainer.use_cases.subscription_lifecycle,
    )
    calendars: CalendarSyncOrchestratorsContainer = Container(  # type: ignore[assignment]
        CalendarSyncOrchestratorsContainer,
        calendar_use_cases=CoreOrchestratorsContainer.use_cases.calendars,
    )
    value: ValueOrchestratorsContainer = Container(  # type: ignore[assignment]
        ValueOrchestratorsContainer,
        value_use_cases=CoreOrchestratorsContainer.use_cases.value,
    )
