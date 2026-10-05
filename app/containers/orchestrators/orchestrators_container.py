from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.orchestrators.account_orchestrators import (
    AccountOrchestratorsContainer,
)
from app.containers.orchestrators.analytics_orchestrators import (
    AnalyticsOrchestratorsContainer,
)
from app.containers.orchestrators.assistant_orchestrators import (
    AssistantOrchestratorsContainer,
)
from app.containers.orchestrators.billing_orchestrators import (
    BillingOrchestratorsContainer,
)
from app.containers.orchestrators.booking_link_orchestrators import (
    BookingLinkOrchestratorsContainer,
)
from app.containers.orchestrators.call_orchestrators import (
    CallOrchestratorsContainer,
)
from app.containers.orchestrators.channel_orchestrators import (
    ChannelOrchestratorsContainer,
)
from app.containers.orchestrators.compliance_orchestrators import (
    ComplianceOrchestratorsContainer,
)
from app.containers.orchestrators.conversation_orchestrators import (
    ConversationOrchestratorsContainer,
)
from app.containers.orchestrators.demo_orchestrators import DemoOrchestratorsContainer
from app.containers.orchestrators.feedback_orchestrators import (
    FeedbackOrchestratorsContainer,
)
from app.containers.orchestrators.inbox_orchestrators import (
    InboxOrchestratorsContainer,
)
from app.containers.orchestrators.knowledge_orchestrators import (
    KnowledgeOrchestratorsContainer,
)
from app.containers.orchestrators.legal_orchestrators import (
    LegalOrchestratorsContainer,
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
from app.containers.orchestrators.platform_ops_orchestrators import (
    PlatformOpsOrchestratorsContainer,
)
from app.containers.orchestrators.platform_orchestrators import (
    PlatformOrchestratorsContainer,
)
from app.containers.orchestrators.privacy_orchestrators import (
    PrivacyOrchestratorsContainer,
)
from app.containers.orchestrators.public_demo_orchestrators import (
    PublicDemoOrchestratorsContainer,
)
from app.containers.orchestrators.security_orchestrators import (
    SecurityOrchestratorsContainer,
)
from app.containers.orchestrators.setup_orchestrators import (
    SetupOrchestratorsContainer,
)
from app.containers.orchestrators.sharing_orchestrators import (
    SharingOrchestratorsContainer,
)
from app.containers.orchestrators.value_orchestrators import (
    ValueOrchestratorsContainer,
)
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer
from app.containers.utilities import UtilitiesContainer


class OrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators, one child container per bounded context: the generic one
    around each single-use-case endpoint and the dedicated ones that
    coordinate several use cases.

    The autotest scenario runner is a use case of the assembly module, but it
    drives the conversation turn orchestrator, so it is wired with the
    assistant orchestrators (the use cases container cannot depend on
    orchestrators).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    use_cases: UseCasesContainer = composed_container_edge(UseCasesContainer)  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountOrchestratorsContainer = Container(  # type: ignore[assignment]
        AccountOrchestratorsContainer,
        account_use_cases=use_cases.accounts,
        catalog_use_cases=use_cases.catalog,
        assistant_use_cases=use_cases.assistants,
    )
    compliance: ComplianceOrchestratorsContainer = Container(  # type: ignore[assignment]
        ComplianceOrchestratorsContainer,
        compliance_use_cases=use_cases.compliance,
    )
    privacy: PrivacyOrchestratorsContainer = Container(  # type: ignore[assignment]
        PrivacyOrchestratorsContainer,
        privacy_use_cases=use_cases.privacy,
    )
    legal: LegalOrchestratorsContainer = Container(  # type: ignore[assignment]
        LegalOrchestratorsContainer,
        legal_use_cases=use_cases.legal,
    )
    public_demos: PublicDemoOrchestratorsContainer = Container(  # type: ignore[assignment]
        PublicDemoOrchestratorsContainer,
        public_demo_use_cases=use_cases.public_demos,
        utilities=utilities,
    )
    inbox: InboxOrchestratorsContainer = Container(  # type: ignore[assignment]
        InboxOrchestratorsContainer,
        inbox_use_cases=use_cases.inbox,
    )
    memory: MemoryOrchestratorsContainer = Container(  # type: ignore[assignment]
        MemoryOrchestratorsContainer,
        memory_use_cases=use_cases.memory,
    )
    knowledge: KnowledgeOrchestratorsContainer = Container(  # type: ignore[assignment]
        KnowledgeOrchestratorsContainer,
        knowledge_use_cases=use_cases.knowledge,
        menu_import_use_cases=use_cases.menu_import,
        scheduling_use_cases=use_cases.scheduling,
    )
    operations: OperationsOrchestratorsContainer = Container(  # type: ignore[assignment]
        OperationsOrchestratorsContainer,
        scheduling_use_cases=use_cases.scheduling,
        booking_use_cases=use_cases.bookings,
        follow_up_use_cases=use_cases.follow_ups,
    )
    calls: CallOrchestratorsContainer = Container(  # type: ignore[assignment]
        CallOrchestratorsContainer,
        call_use_cases=use_cases.calls,
    )
    conversations: ConversationOrchestratorsContainer = Container(  # type: ignore[assignment]
        ConversationOrchestratorsContainer,
        utilities=utilities,
        account_use_cases=use_cases.accounts,
        follow_up_use_cases=use_cases.follow_ups,
        conversation_use_cases=use_cases.conversations,
        conversation_feed_use_cases=use_cases.conversation_feed,
        voice_use_cases=use_cases.voice,
        delivery_use_cases=use_cases.deliveries,
        call_use_cases=use_cases.calls,
        call_orchestrators=calls,
        feedback_use_cases=use_cases.feedback,
    )
    assistants: AssistantOrchestratorsContainer = Container(  # type: ignore[assignment]
        AssistantOrchestratorsContainer,
        adapters=adapters,
        config=config,
        repositories=repositories,
        assistant_use_cases=use_cases.assistants,
        autotest_use_cases=use_cases.autotests,
        apply_use_cases=use_cases.apply,
        pending_change_use_cases=use_cases.pending_changes,
        conversation_orchestrators=conversations,
    )
    setup: SetupOrchestratorsContainer = Container(  # type: ignore[assignment]
        SetupOrchestratorsContainer,
        setup_use_cases=use_cases.setup,
        launch_use_cases=use_cases.launch,
        guide_use_cases=use_cases.guide,
    )
    channels: ChannelOrchestratorsContainer = Container(  # type: ignore[assignment]
        ChannelOrchestratorsContainer,
        channel_use_cases=use_cases.channels,
        delivery_use_cases=use_cases.deliveries,
        follow_up_use_cases=use_cases.follow_ups,
        conversation_use_cases=use_cases.conversations,
        reply_speed_use_cases=use_cases.reply_speed,
        config=config,
        facilitators=facilitators,
        time_provider=time_provider,
        utilities=utilities,
    )
    billing: BillingOrchestratorsContainer = Container(  # type: ignore[assignment]
        BillingOrchestratorsContainer,
        billing_use_cases=use_cases.billing,
        invoicing_use_cases=use_cases.invoicing,
    )
    notifications: NotificationOrchestratorsContainer = Container(  # type: ignore[assignment]
        NotificationOrchestratorsContainer,
        notification_use_cases=use_cases.notifications,
        delivery_use_cases=use_cases.deliveries,
    )
    platform: PlatformOrchestratorsContainer = Container(  # type: ignore[assignment]
        PlatformOrchestratorsContainer,
        platform_use_cases=use_cases.platform,
    )
    platform_ops: PlatformOpsOrchestratorsContainer = Container(  # type: ignore[assignment]
        PlatformOpsOrchestratorsContainer,
        platform_ops_use_cases=use_cases.platform_ops,
        help_use_cases=use_cases.help,
    )
    security: SecurityOrchestratorsContainer = Container(  # type: ignore[assignment]
        SecurityOrchestratorsContainer,
        security_use_cases=use_cases.security,
        mfa_use_cases=use_cases.mfa,
    )
    sharing: SharingOrchestratorsContainer = Container(  # type: ignore[assignment]
        SharingOrchestratorsContainer,
        sharing_use_cases=use_cases.sharing,
        follow_up_use_cases=use_cases.follow_ups,
        utilities=utilities,
    )
    booking_links: BookingLinkOrchestratorsContainer = Container(  # type: ignore[assignment]
        BookingLinkOrchestratorsContainer,
        booking_link_use_cases=use_cases.booking_links,
        utilities=utilities,
    )
    feedback: FeedbackOrchestratorsContainer = Container(  # type: ignore[assignment]
        FeedbackOrchestratorsContainer,
        feedback_use_cases=use_cases.feedback,
    )
    analytics: AnalyticsOrchestratorsContainer = Container(  # type: ignore[assignment]
        AnalyticsOrchestratorsContainer,
        analytics_use_cases=use_cases.analytics,
    )
    demo: DemoOrchestratorsContainer = Container(  # type: ignore[assignment]
        DemoOrchestratorsContainer,
        demo_use_cases=use_cases.demo,
        assistant_use_cases=use_cases.assistants,
    )
    value: ValueOrchestratorsContainer = Container(  # type: ignore[assignment]
        ValueOrchestratorsContainer,
        value_use_cases=use_cases.value,
    )
