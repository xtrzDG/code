from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.container_edges import composed_container_edge
from app.containers.orchestrators.orchestrators_container import (
    OrchestratorsContainer,
)
from app.containers.pipelines.account_pipelines import AccountPipelinesContainer
from app.containers.pipelines.admin_action_pipelines import (
    AdminActionPipelinesContainer,
)
from app.containers.pipelines.analytics_pipelines import AnalyticsPipelinesContainer
from app.containers.pipelines.assistant_pipelines import AssistantPipelinesContainer
from app.containers.pipelines.billing_pipelines import BillingPipelinesContainer
from app.containers.pipelines.booking_link_pipelines import (
    BookingLinkPipelinesContainer,
)
from app.containers.pipelines.calendar_sync_pipelines import (
    CalendarSyncPipelinesContainer,
)
from app.containers.pipelines.call_pipelines import CallPipelinesContainer
from app.containers.pipelines.channel_pipelines import ChannelPipelinesContainer
from app.containers.pipelines.compliance_pipelines import CompliancePipelinesContainer
from app.containers.pipelines.conversation_pipelines import (
    ConversationPipelinesContainer,
)
from app.containers.pipelines.customer_pipelines import CustomerPipelinesContainer
from app.containers.pipelines.demo_pipelines import DemoPipelinesContainer
from app.containers.pipelines.feedback_pipelines import FeedbackPipelinesContainer
from app.containers.pipelines.growth_pipelines import GrowthPipelinesContainer
from app.containers.pipelines.inbox_pipelines import InboxPipelinesContainer
from app.containers.pipelines.knowledge_pipelines import KnowledgePipelinesContainer
from app.containers.pipelines.legal_pipelines import LegalPipelinesContainer
from app.containers.pipelines.memory_pipelines import MemoryPipelinesContainer
from app.containers.pipelines.notification_pipelines import (
    NotificationPipelinesContainer,
)
from app.containers.pipelines.operations_pipelines import OperationsPipelinesContainer
from app.containers.pipelines.platform_ops_pipelines import (
    PlatformOpsPipelinesContainer,
)
from app.containers.pipelines.platform_pipelines import PlatformPipelinesContainer
from app.containers.pipelines.privacy_pipelines import PrivacyPipelinesContainer
from app.containers.pipelines.public_demo_pipelines import (
    PublicDemoPipelinesContainer,
)
from app.containers.pipelines.referral_pipelines import ReferralPipelinesContainer
from app.containers.pipelines.security_pipelines import SecurityPipelinesContainer
from app.containers.pipelines.setup_pipelines import SetupPipelinesContainer
from app.containers.pipelines.sharing_pipelines import SharingPipelinesContainer
from app.containers.pipelines.spend_guard_pipelines import (
    SpendGuardPipelinesContainer,
)
from app.containers.pipelines.value_pipelines import ValuePipelinesContainer
from app.containers.registries import RegistriesContainer
from app.containers.use_cases.use_cases_container import UseCasesContainer


class PipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines, one child container per bounded context: the generic one
    around each orchestrator and the dedicated phases (assembly then
    autotests, the customer message, the owner's test chat).

    The channel webhook and widget orchestrators hand every customer message
    to the customer-message pipeline, so they are wired with the channel
    pipelines, which take the conversation pipelines as an edge.
    """

    orchestrators: OrchestratorsContainer = composed_container_edge(  # type: ignore[assignment]
        OrchestratorsContainer
    )
    use_cases: UseCasesContainer = composed_container_edge(UseCasesContainer)  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountPipelinesContainer = Container(  # type: ignore[assignment]
        AccountPipelinesContainer,
        account_orchestrators=orchestrators.accounts,
    )
    compliance: CompliancePipelinesContainer = Container(  # type: ignore[assignment]
        CompliancePipelinesContainer,
        compliance_orchestrators=orchestrators.compliance,
    )
    privacy: PrivacyPipelinesContainer = Container(  # type: ignore[assignment]
        PrivacyPipelinesContainer,
        privacy_orchestrators=orchestrators.privacy,
    )
    legal: LegalPipelinesContainer = Container(  # type: ignore[assignment]
        LegalPipelinesContainer,
        legal_orchestrators=orchestrators.legal,
    )
    inbox: InboxPipelinesContainer = Container(  # type: ignore[assignment]
        InboxPipelinesContainer,
        inbox=orchestrators.inbox,
    )
    memory: MemoryPipelinesContainer = Container(  # type: ignore[assignment]
        MemoryPipelinesContainer,
        memory=orchestrators.memory,
    )
    customers: CustomerPipelinesContainer = Container(  # type: ignore[assignment]
        CustomerPipelinesContainer,
        customers=orchestrators.customers,
    )
    knowledge: KnowledgePipelinesContainer = Container(  # type: ignore[assignment]
        KnowledgePipelinesContainer,
        knowledge_orchestrators=orchestrators.knowledge,
    )
    operations: OperationsPipelinesContainer = Container(  # type: ignore[assignment]
        OperationsPipelinesContainer,
        operations_orchestrators=orchestrators.operations,
    )
    conversations: ConversationPipelinesContainer = Container(  # type: ignore[assignment]
        ConversationPipelinesContainer,
        conversation_orchestrators=orchestrators.conversations,
        registries=registries,
        setup_orchestrators=orchestrators.setup,
    )
    public_demos: PublicDemoPipelinesContainer = Container(  # type: ignore[assignment]
        PublicDemoPipelinesContainer,
        public_demo_orchestrators=orchestrators.public_demos,
        conversation_orchestrators=orchestrators.conversations,
        registries=registries,
    )
    assistants: AssistantPipelinesContainer = Container(  # type: ignore[assignment]
        AssistantPipelinesContainer,
        assistant_orchestrators=orchestrators.assistants,
        registries=registries,
    )
    setup: SetupPipelinesContainer = Container(  # type: ignore[assignment]
        SetupPipelinesContainer,
        setup_orchestrators=orchestrators.setup,
    )
    channels: ChannelPipelinesContainer = Container(  # type: ignore[assignment]
        ChannelPipelinesContainer,
        channel_orchestrators=orchestrators.channels,
        channel_use_cases=use_cases.channels,
        delivery_use_cases=use_cases.deliveries,
        reply_speed_use_cases=use_cases.reply_speed,
        conversation_pipelines=conversations,
    )
    billing: BillingPipelinesContainer = Container(  # type: ignore[assignment]
        BillingPipelinesContainer,
        billing_orchestrators=orchestrators.billing,
    )
    calls: CallPipelinesContainer = Container(  # type: ignore[assignment]
        CallPipelinesContainer,
        calls=orchestrators.calls,
    )
    notifications: NotificationPipelinesContainer = Container(  # type: ignore[assignment]
        NotificationPipelinesContainer,
        notifications=orchestrators.notifications,
    )
    platform: PlatformPipelinesContainer = Container(  # type: ignore[assignment]
        PlatformPipelinesContainer,
        platform_orchestrators=orchestrators.platform,
    )
    platform_ops: PlatformOpsPipelinesContainer = Container(  # type: ignore[assignment]
        PlatformOpsPipelinesContainer,
        platform_ops=orchestrators.platform_ops,
    )
    spend_guard: SpendGuardPipelinesContainer = Container(  # type: ignore[assignment]
        SpendGuardPipelinesContainer,
        spend_guard=orchestrators.spend_guard,
    )
    admin_actions: AdminActionPipelinesContainer = Container(  # type: ignore[assignment]
        AdminActionPipelinesContainer,
        admin_actions=orchestrators.admin_actions,
    )
    security: SecurityPipelinesContainer = Container(  # type: ignore[assignment]
        SecurityPipelinesContainer,
        security_orchestrators=orchestrators.security,
    )
    sharing: SharingPipelinesContainer = Container(  # type: ignore[assignment]
        SharingPipelinesContainer,
        sharing_orchestrators=orchestrators.sharing,
        registries=registries,
    )
    booking_links: BookingLinkPipelinesContainer = Container(  # type: ignore[assignment]
        BookingLinkPipelinesContainer,
        booking_link_orchestrators=orchestrators.booking_links,
    )
    feedback: FeedbackPipelinesContainer = Container(  # type: ignore[assignment]
        FeedbackPipelinesContainer,
        feedback=orchestrators.feedback,
    )
    growth: GrowthPipelinesContainer = Container(  # type: ignore[assignment]
        GrowthPipelinesContainer,
        growth=orchestrators.growth,
    )
    calendars: CalendarSyncPipelinesContainer = Container(  # type: ignore[assignment]
        CalendarSyncPipelinesContainer, calendars=orchestrators.calendars
    )  # fmt: skip
    analytics: AnalyticsPipelinesContainer = Container(  # type: ignore[assignment]
        AnalyticsPipelinesContainer,
        analytics=orchestrators.analytics,
    )
    demo: DemoPipelinesContainer = Container(  # type: ignore[assignment]
        DemoPipelinesContainer,
        demo_orchestrators=orchestrators.demo,
    )
    value: ValuePipelinesContainer = Container(  # type: ignore[assignment]
        ValuePipelinesContainer,
        value=orchestrators.value,
    )
    referrals: ReferralPipelinesContainer = Container(  # type: ignore[assignment]
        ReferralPipelinesContainer,
        referrals=orchestrators.referrals,
    )
