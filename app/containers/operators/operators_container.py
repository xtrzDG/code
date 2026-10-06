from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.container_edges import composed_container_edge
from app.containers.operators.account_operators import AccountOperatorsContainer
from app.containers.operators.admin_action_operators import (
    AdminActionOperatorsContainer,
)
from app.containers.operators.analytics_operators import AnalyticsOperatorsContainer
from app.containers.operators.assistant_operators import AssistantOperatorsContainer
from app.containers.operators.billing_operators import BillingOperatorsContainer
from app.containers.operators.booking_link_operators import (
    BookingLinkOperatorsContainer,
)
from app.containers.operators.calendar_sync_operators import (
    CalendarSyncOperatorsContainer,
)
from app.containers.operators.call_operators import CallOperatorsContainer
from app.containers.operators.channel_operators import ChannelOperatorsContainer
from app.containers.operators.compliance_operators import ComplianceOperatorsContainer
from app.containers.operators.conversation_operators import (
    ConversationOperatorsContainer,
)
from app.containers.operators.customer_operators import CustomerOperatorsContainer
from app.containers.operators.data_task_operators import DataTaskOperatorsContainer
from app.containers.operators.demo_operators import DemoOperatorsContainer
from app.containers.operators.feedback_operators import FeedbackOperatorsContainer
from app.containers.operators.growth_operators import GrowthOperatorsContainer
from app.containers.operators.idempotency_operators import (
    IdempotencyOperatorsContainer,
)
from app.containers.operators.inbox_operators import InboxOperatorsContainer
from app.containers.operators.knowledge_operators import KnowledgeOperatorsContainer
from app.containers.operators.legal_operators import LegalOperatorsContainer
from app.containers.operators.memory_operators import MemoryOperatorsContainer
from app.containers.operators.notification_operators import (
    NotificationOperatorsContainer,
)
from app.containers.operators.operations_operators import OperationsOperatorsContainer
from app.containers.operators.platform_operators import PlatformOperatorsContainer
from app.containers.operators.platform_ops_operators import (
    PlatformOpsOperatorsContainer,
)
from app.containers.operators.privacy_operators import PrivacyOperatorsContainer
from app.containers.operators.public_demo_operators import (
    PublicDemoOperatorsContainer,
)
from app.containers.operators.referral_operators import ReferralOperatorsContainer
from app.containers.operators.security_operators import SecurityOperatorsContainer
from app.containers.operators.setup_operators import SetupOperatorsContainer
from app.containers.operators.sharing_operators import SharingOperatorsContainer
from app.containers.operators.spend_guard_operators import (
    SpendGuardOperatorsContainer,
)
from app.containers.operators.subscription_lifecycle_operators import (
    SubscriptionLifecycleOperatorsContainer,
)
from app.containers.operators.telemetry_operators import TelemetryOperatorsContainer
from app.containers.operators.value_operators import ValueOperatorsContainer
from app.containers.pipelines.pipelines_container import PipelinesContainer
from app.containers.utilities import UtilitiesContainer


class OperatorsContainer(containers.DeclarativeContainer):
    """
    One operator per HTTP endpoint and per worker job, one child container
    per bounded context. Each runs its pipeline synchronously, inside the
    storage scope of the business its input names (row-level security on
    Postgres); input and output types come from the use case or
    orchestrator at the bottom of the chain.
    """

    pipelines: PipelinesContainer = composed_container_edge(PipelinesContainer)  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountOperatorsContainer = Container(  # type: ignore[assignment]
        AccountOperatorsContainer,
        account_pipelines=pipelines.accounts,
        utilities=utilities,
    )
    compliance: ComplianceOperatorsContainer = Container(  # type: ignore[assignment]
        ComplianceOperatorsContainer,
        compliance_pipelines=pipelines.compliance,
        utilities=utilities,
    )
    privacy: PrivacyOperatorsContainer = Container(  # type: ignore[assignment]
        PrivacyOperatorsContainer,
        privacy_pipelines=pipelines.privacy,
        utilities=utilities,
    )
    legal: LegalOperatorsContainer = Container(  # type: ignore[assignment]
        LegalOperatorsContainer,
        legal_pipelines=pipelines.legal,
        utilities=utilities,
    )
    public_demos: PublicDemoOperatorsContainer = Container(  # type: ignore[assignment]
        PublicDemoOperatorsContainer,
        public_demo_pipelines=pipelines.public_demos,
        utilities=utilities,
    )
    inbox: InboxOperatorsContainer = Container(  # type: ignore[assignment]
        InboxOperatorsContainer,
        inbox_pipelines=pipelines.inbox,
        utilities=utilities,
    )
    memory: MemoryOperatorsContainer = Container(  # type: ignore[assignment]
        MemoryOperatorsContainer,
        memory_pipelines=pipelines.memory,
        utilities=utilities,
    )
    customers: CustomerOperatorsContainer = Container(  # type: ignore[assignment]
        CustomerOperatorsContainer,
        customer_pipelines=pipelines.customers,
        utilities=utilities,
    )
    knowledge: KnowledgeOperatorsContainer = Container(  # type: ignore[assignment]
        KnowledgeOperatorsContainer,
        knowledge_pipelines=pipelines.knowledge,
        utilities=utilities,
    )
    operations: OperationsOperatorsContainer = Container(  # type: ignore[assignment]
        OperationsOperatorsContainer,
        operations_pipelines=pipelines.operations,
        utilities=utilities,
    )
    conversations: ConversationOperatorsContainer = Container(  # type: ignore[assignment]
        ConversationOperatorsContainer,
        conversation_pipelines=pipelines.conversations,
        utilities=utilities,
    )
    assistants: AssistantOperatorsContainer = Container(  # type: ignore[assignment]
        AssistantOperatorsContainer,
        assistant_pipelines=pipelines.assistants,
        utilities=utilities,
    )
    setup: SetupOperatorsContainer = Container(  # type: ignore[assignment]
        SetupOperatorsContainer,
        setup_pipelines=pipelines.setup,
        utilities=utilities,
    )
    channels: ChannelOperatorsContainer = Container(  # type: ignore[assignment]
        ChannelOperatorsContainer,
        channel_pipelines=pipelines.channels,
        utilities=utilities,
    )
    billing: BillingOperatorsContainer = Container(  # type: ignore[assignment]
        BillingOperatorsContainer,
        billing_pipelines=pipelines.billing,
        utilities=utilities,
    )
    calls: CallOperatorsContainer = Container(  # type: ignore[assignment]
        CallOperatorsContainer,
        call_pipelines=pipelines.calls,
        utilities=utilities,
    )
    notifications: NotificationOperatorsContainer = Container(  # type: ignore[assignment]
        NotificationOperatorsContainer,
        notification_pipelines=pipelines.notifications,
        utilities=utilities,
    )
    platform: PlatformOperatorsContainer = Container(  # type: ignore[assignment]
        PlatformOperatorsContainer,
        platform_pipelines=pipelines.platform,
        utilities=utilities,
    )
    data_tasks: DataTaskOperatorsContainer = Container(  # type: ignore[assignment]
        DataTaskOperatorsContainer,
        data_task_pipelines=pipelines.data_tasks,
        utilities=utilities,
    )
    telemetry: TelemetryOperatorsContainer = Container(  # type: ignore[assignment]
        TelemetryOperatorsContainer,
        telemetry_pipelines=pipelines.telemetry,
        utilities=utilities,
    )
    idempotency: IdempotencyOperatorsContainer = Container(  # type: ignore[assignment]
        IdempotencyOperatorsContainer,
        idempotency_pipelines=pipelines.idempotency,
        utilities=utilities,
    )
    platform_ops: PlatformOpsOperatorsContainer = Container(  # type: ignore[assignment]
        PlatformOpsOperatorsContainer,
        platform_ops_pipelines=pipelines.platform_ops,
        utilities=utilities,
    )
    spend_guard: SpendGuardOperatorsContainer = Container(  # type: ignore[assignment]
        SpendGuardOperatorsContainer,
        spend_guard_pipelines=pipelines.spend_guard,
        utilities=utilities,
    )
    admin_actions: AdminActionOperatorsContainer = Container(  # type: ignore[assignment]
        AdminActionOperatorsContainer,
        admin_action_pipelines=pipelines.admin_actions,
        utilities=utilities,
    )
    security: SecurityOperatorsContainer = Container(  # type: ignore[assignment]
        SecurityOperatorsContainer,
        security_pipelines=pipelines.security,
        utilities=utilities,
    )
    sharing: SharingOperatorsContainer = Container(  # type: ignore[assignment]
        SharingOperatorsContainer,
        sharing_pipelines=pipelines.sharing,
        utilities=utilities,
    )
    booking_links: BookingLinkOperatorsContainer = Container(  # type: ignore[assignment]
        BookingLinkOperatorsContainer,
        booking_link_pipelines=pipelines.booking_links,
        utilities=utilities,
    )
    feedback: FeedbackOperatorsContainer = Container(  # type: ignore[assignment]
        FeedbackOperatorsContainer,
        feedback_pipelines=pipelines.feedback,
        utilities=utilities,
    )
    growth: GrowthOperatorsContainer = Container(  # type: ignore[assignment]
        GrowthOperatorsContainer,
        growth_pipelines=pipelines.growth,
        utilities=utilities,
    )
    lifecycle: SubscriptionLifecycleOperatorsContainer = Container(  # type: ignore[assignment]
        SubscriptionLifecycleOperatorsContainer,
        pipelines=pipelines.lifecycle,
        utilities=utilities,
    )
    calendars: CalendarSyncOperatorsContainer = Container(  # type: ignore[assignment]
        CalendarSyncOperatorsContainer,
        calendar_pipelines=pipelines.calendars,
        utilities=utilities,
    )
    analytics: AnalyticsOperatorsContainer = Container(  # type: ignore[assignment]
        AnalyticsOperatorsContainer,
        analytics_pipelines=pipelines.analytics,
        utilities=utilities,
    )
    demo: DemoOperatorsContainer = Container(  # type: ignore[assignment]
        DemoOperatorsContainer,
        demo_pipelines=pipelines.demo,
        utilities=utilities,
    )
    value: ValueOperatorsContainer = Container(  # type: ignore[assignment]
        ValueOperatorsContainer,
        value_pipelines=pipelines.value,
        utilities=utilities,
    )
    referrals: ReferralOperatorsContainer = Container(  # type: ignore[assignment]
        ReferralOperatorsContainer,
        referral_pipelines=pipelines.referrals,
        utilities=utilities,
    )
