from dependency_injector.providers import Container, Factory

from app.containers.use_cases.analytics_use_cases import AnalyticsUseCasesContainer
from app.containers.use_cases.apply_use_cases import ApplyUseCasesContainer
from app.containers.use_cases.assistant_use_cases import AssistantUseCasesContainer
from app.containers.use_cases.autotest_use_cases import AutotestUseCasesContainer
from app.containers.use_cases.billing_use_cases import BillingUseCasesContainer
from app.containers.use_cases.call_use_cases import CallUseCasesContainer
from app.containers.use_cases.channel_use_cases import ChannelUseCasesContainer
from app.containers.use_cases.conversation_feed_use_cases import (
    ConversationFeedUseCasesContainer,
)
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.core_use_cases_container import CoreUseCasesContainer
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.demo_use_cases import DemoUseCasesContainer
from app.containers.use_cases.feedback_use_cases import FeedbackUseCasesContainer
from app.containers.use_cases.guide_use_cases import GuideUseCasesContainer
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.use_cases.notification_use_cases import (
    NotificationUseCasesContainer,
)
from app.containers.use_cases.pending_change_use_cases import (
    PendingChangeUseCasesContainer,
)
from app.containers.use_cases.platform_ops_use_cases import (
    PlatformOpsUseCasesContainer,
)
from app.containers.use_cases.platform_use_cases import PlatformUseCasesContainer
from app.containers.use_cases.security_use_cases import SecurityUseCasesContainer
from app.containers.use_cases.setup_use_cases import SetupUseCasesContainer
from app.containers.use_cases.sharing_use_cases import SharingUseCasesContainer
from app.containers.use_cases.value_use_cases import ValueUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer
from app.use_cases.example_use_case import ExampleUseCase


class UseCasesContainer(CoreUseCasesContainer):
    """
    Every use case, one child container per bounded context, typed by its
    contract (input and output), so the orchestrator, pipeline and operator
    chains built on them are checked. The edges and the contexts the others
    build on come from `CoreUseCasesContainer`.

    Use cases are stateless: Factory, except the ones holding a cache. A
    context that runs another context's use cases gets that child container
    as an edge, so the order below is the order of those dependencies.
    """

    conversations: ConversationUseCasesContainer = Container(  # type: ignore[assignment]
        ConversationUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        knowledge_use_cases=CoreUseCasesContainer.knowledge,
        booking_use_cases=CoreUseCasesContainer.bookings,
        follow_up_use_cases=CoreUseCasesContainer.follow_ups,
    )
    conversation_feed: ConversationFeedUseCasesContainer = Container(  # type: ignore[assignment]
        ConversationFeedUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    voice: VoiceUseCasesContainer = Container(  # type: ignore[assignment]
        VoiceUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        conversation_use_cases=conversations,
        follow_up_use_cases=CoreUseCasesContainer.follow_ups,
    )
    calls: CallUseCasesContainer = Container(  # type: ignore[assignment]
        CallUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    launch: LaunchUseCasesContainer = Container(  # type: ignore[assignment]
        LaunchUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
    )
    pending_changes: PendingChangeUseCasesContainer = Container(  # type: ignore[assignment]
        PendingChangeUseCasesContainer,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    assistants: AssistantUseCasesContainer = Container(  # type: ignore[assignment]
        AssistantUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        conversation_use_cases=conversations,
        voice_use_cases=voice,
        launch_use_cases=launch,
        pending_change_use_cases=pending_changes,
    )
    apply: ApplyUseCasesContainer = Container(  # type: ignore[assignment]
        ApplyUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        assistant_use_cases=assistants,
        pending_change_use_cases=pending_changes,
    )
    setup: SetupUseCasesContainer = Container(  # type: ignore[assignment]
        SetupUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        config=CoreUseCasesContainer.config,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        assistant_use_cases=assistants,
        apply_use_cases=apply,
        launch_use_cases=launch,
    )
    guide: GuideUseCasesContainer = Container(  # type: ignore[assignment]
        GuideUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        account_use_cases=CoreUseCasesContainer.accounts,
        setup_use_cases=setup,
    )
    autotests: AutotestUseCasesContainer = Container(  # type: ignore[assignment]
        AutotestUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    channels: ChannelUseCasesContainer = Container(  # type: ignore[assignment]
        ChannelUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        voice_use_cases=voice,
    )
    deliveries: DeliveryUseCasesContainer = Container(  # type: ignore[assignment]
        DeliveryUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
    )
    notifications: NotificationUseCasesContainer = Container(  # type: ignore[assignment]
        NotificationUseCasesContainer,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    billing: BillingUseCasesContainer = Container(  # type: ignore[assignment]
        BillingUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
        voice_use_cases=voice,
    )
    platform: PlatformUseCasesContainer = Container(  # type: ignore[assignment]
        PlatformUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        billing_use_cases=billing,
    )
    security: SecurityUseCasesContainer = Container(  # type: ignore[assignment]
        SecurityUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        platform_use_cases=platform,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    platform_ops: PlatformOpsUseCasesContainer = Container(  # type: ignore[assignment]
        PlatformOpsUseCasesContainer, adapters=CoreUseCasesContainer.adapters,
        clients=CoreUseCasesContainer.clients, config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities, platform_use_cases=platform,
    )  # fmt: skip
    sharing: SharingUseCasesContainer = Container(  # type: ignore[assignment]
        SharingUseCasesContainer,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    value: ValueUseCasesContainer = Container(  # type: ignore[assignment]
        ValueUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    feedback: FeedbackUseCasesContainer = Container(  # type: ignore[assignment]
        FeedbackUseCasesContainer,
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        utilities=CoreUseCasesContainer.utilities,
        account_use_cases=CoreUseCasesContainer.accounts,
    )
    analytics: AnalyticsUseCasesContainer = Container(  # type: ignore[assignment]
        AnalyticsUseCasesContainer,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        billing_use_cases=billing,
        platform_use_cases=platform,
    )
    demo: DemoUseCasesContainer = Container(  # type: ignore[assignment]
        DemoUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        config=CoreUseCasesContainer.config,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
    )

    # --- Template example (keeps its concrete type).
    example_use_case: Factory[ExampleUseCase] = Factory(ExampleUseCase)
