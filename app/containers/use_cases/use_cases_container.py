from dependency_injector import containers
from dependency_injector.providers import Container, DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.containers.use_cases.apply_use_cases import ApplyUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.autotest_use_cases import AutotestUseCasesContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.catalog_use_cases import CatalogUseCasesContainer
from app.containers.use_cases.channel_use_cases import ChannelUseCasesContainer
from app.containers.use_cases.compliance_use_cases import ComplianceUseCasesContainer
from app.containers.use_cases.conversation_feed_use_cases import (
    ConversationFeedUseCasesContainer,
)
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.demo_use_cases import DemoUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.knowledge_use_cases import KnowledgeUseCasesContainer
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.use_cases.menu_import_use_cases import MenuImportUseCasesContainer
from app.containers.use_cases.notification_use_cases import (
    NotificationUseCasesContainer,
)
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.use_cases.scheduling_use_cases import SchedulingUseCasesContainer
from app.containers.use_cases.setup_use_cases import SetupUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.use_cases.example_use_case import ExampleUseCase


class UseCasesContainer(containers.DeclarativeContainer):
    """
    Every use case, one child container per bounded context, typed by its
    contract (input and output), so the orchestrator, pipeline and operator
    chains built on them are checked.

    Use cases are stateless: Factory, except the ones holding a cache. A
    context that runs another context's use cases gets that child container
    as an edge, so the order below is the order of those dependencies.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    accounts: AccountUseCasesContainer = Container(  # type: ignore[assignment]
        AccountUseCasesContainer,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    catalog: CatalogUseCasesContainer = Container(  # type: ignore[assignment]
        CatalogUseCasesContainer,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    compliance: ComplianceUseCasesContainer = Container(  # type: ignore[assignment]
        ComplianceUseCasesContainer,
        adapters=adapters,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
    )
    knowledge: KnowledgeUseCasesContainer = Container(  # type: ignore[assignment]
        KnowledgeUseCasesContainer,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
    )
    menu_import: MenuImportUseCasesContainer = Container(  # type: ignore[assignment]
        MenuImportUseCasesContainer,
        adapters=adapters,
        repositories=repositories,
        time_provider=time_provider,
        account_use_cases=accounts,
    )
    scheduling: SchedulingUseCasesContainer = Container(  # type: ignore[assignment]
        SchedulingUseCasesContainer,
        adapters=adapters,
        clients=clients,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
    )
    bookings: BookingUseCasesContainer = Container(  # type: ignore[assignment]
        BookingUseCasesContainer,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    follow_ups: FollowUpUseCasesContainer = Container(  # type: ignore[assignment]
        FollowUpUseCasesContainer,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
    )
    conversations: ConversationUseCasesContainer = Container(  # type: ignore[assignment]
        ConversationUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        knowledge_use_cases=knowledge,
        booking_use_cases=bookings,
        follow_up_use_cases=follow_ups,
    )
    conversation_feed: ConversationFeedUseCasesContainer = Container(  # type: ignore[assignment]
        ConversationFeedUseCasesContainer,
        adapters=adapters,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        account_use_cases=accounts,
    )
    voice: VoiceUseCasesContainer = Container(  # type: ignore[assignment]
        VoiceUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        conversation_use_cases=conversations,
        follow_up_use_cases=follow_ups,
    )
    launch: LaunchUseCasesContainer = Container(  # type: ignore[assignment]
        LaunchUseCasesContainer,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
    )
    assistants: AssistantUseCasesContainer = Container(  # type: ignore[assignment]
        AssistantUseCasesContainer,
        adapters=adapters,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
        account_use_cases=accounts,
        conversation_use_cases=conversations,
        voice_use_cases=voice,
        launch_use_cases=launch,
    )
    apply: ApplyUseCasesContainer = Container(  # type: ignore[assignment]
        ApplyUseCasesContainer,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
        assistant_use_cases=assistants,
    )
    setup: SetupUseCasesContainer = Container(  # type: ignore[assignment]
        SetupUseCasesContainer,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
        assistant_use_cases=assistants,
        apply_use_cases=apply,
        launch_use_cases=launch,
    )
    autotests: AutotestUseCasesContainer = Container(  # type: ignore[assignment]
        AutotestUseCasesContainer,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        account_use_cases=accounts,
    )
    channels: ChannelUseCasesContainer = Container(  # type: ignore[assignment]
        ChannelUseCasesContainer,
        adapters=adapters,
        clients=clients,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        account_use_cases=accounts,
        voice_use_cases=voice,
    )
    deliveries: DeliveryUseCasesContainer = Container(  # type: ignore[assignment]
        DeliveryUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        repositories=repositories,
        time_provider=time_provider,
    )
    notifications: NotificationUseCasesContainer = Container(  # type: ignore[assignment]
        NotificationUseCasesContainer,
        clients=clients,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        account_use_cases=accounts,
    )
    billing: BillingUseCasesContainer = Container(  # type: ignore[assignment]
        BillingUseCasesContainer,
        adapters=adapters,
        config=config,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        transformers=transformers,
        utilities=utilities,
        account_use_cases=accounts,
        voice_use_cases=voice,
    )
    platform: PlatformUseCasesContainer = Container(  # type: ignore[assignment]
        PlatformUseCasesContainer,
        adapters=adapters,
        facilitators=facilitators,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
        utilities=utilities,
        billing_use_cases=billing,
    )
    demo: DemoUseCasesContainer = Container(  # type: ignore[assignment]
        DemoUseCasesContainer,
        adapters=adapters,
        config=config,
        registries=registries,
        repositories=repositories,
        time_provider=time_provider,
    )

    # --- Template example (keeps its concrete type).
    example_use_case: Factory[ExampleUseCase] = Factory(ExampleUseCase)
