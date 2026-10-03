from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer

from app.containers.container_edges import composed_container_edge
from app.containers.orchestrators.orchestrators_container import (
    OrchestratorsContainer,
)
from app.containers.pipelines.account_pipelines import AccountPipelinesContainer
from app.containers.pipelines.assistant_pipelines import AssistantPipelinesContainer
from app.containers.pipelines.billing_pipelines import BillingPipelinesContainer
from app.containers.pipelines.call_pipelines import CallPipelinesContainer
from app.containers.pipelines.channel_pipelines import ChannelPipelinesContainer
from app.containers.pipelines.compliance_pipelines import CompliancePipelinesContainer
from app.containers.pipelines.conversation_pipelines import (
    ConversationPipelinesContainer,
)
from app.containers.pipelines.demo_pipelines import DemoPipelinesContainer
from app.containers.pipelines.inbox_pipelines import InboxPipelinesContainer
from app.containers.pipelines.knowledge_pipelines import KnowledgePipelinesContainer
from app.containers.pipelines.notification_pipelines import (
    NotificationPipelinesContainer,
)
from app.containers.pipelines.operations_pipelines import OperationsPipelinesContainer
from app.containers.pipelines.platform_pipelines import PlatformPipelinesContainer
from app.containers.pipelines.setup_pipelines import SetupPipelinesContainer
from app.containers.pipelines.sharing_pipelines import SharingPipelinesContainer
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
    inbox: InboxPipelinesContainer = Container(  # type: ignore[assignment]
        InboxPipelinesContainer,
        inbox=orchestrators.inbox,
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
    assistants: AssistantPipelinesContainer = Container(  # type: ignore[assignment]
        AssistantPipelinesContainer,
        assistant_orchestrators=orchestrators.assistants,
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
    sharing: SharingPipelinesContainer = Container(  # type: ignore[assignment]
        SharingPipelinesContainer,
        sharing_orchestrators=orchestrators.sharing,
        registries=registries,
    )
    demo: DemoPipelinesContainer = Container(  # type: ignore[assignment]
        DemoPipelinesContainer,
        demo_orchestrators=orchestrators.demo,
    )
