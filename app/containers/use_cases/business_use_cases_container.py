from dependency_injector.providers import Container

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
from app.containers.use_cases.guide_use_cases import GuideUseCasesContainer
from app.containers.use_cases.launch_use_cases import LaunchUseCasesContainer
from app.containers.use_cases.notification_use_cases import (
    NotificationUseCasesContainer,
)
from app.containers.use_cases.pending_change_use_cases import (
    PendingChangeUseCasesContainer,
)
from app.containers.use_cases.setup_use_cases import SetupUseCasesContainer
from app.containers.use_cases.voice_use_cases import VoiceUseCasesContainer


class BusinessUseCasesContainer(CoreUseCasesContainer):
    """
    The use cases of a business's own work, on top of the core contexts:
    conversations and calls, building and launching the assistant, channels,
    deliveries, notifications and billing. `UseCasesContainer` adds the
    platform's contexts (administration, sharing, value, growth) on top.
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
        waitlist_use_cases=CoreUseCasesContainer.waitlist,
    )
    conversation_feed: ConversationFeedUseCasesContainer = Container(  # type: ignore[assignment]
        ConversationFeedUseCasesContainer,
        adapters=CoreUseCasesContainer.adapters,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
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
        spend_guard_use_cases=CoreUseCasesContainer.spend_guard,
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
        config=CoreUseCasesContainer.config,
        facilitators=CoreUseCasesContainer.facilitators,
        registries=CoreUseCasesContainer.registries,
        repositories=CoreUseCasesContainer.repositories,
        time_provider=CoreUseCasesContainer.time_provider,
        transformers=CoreUseCasesContainer.transformers,
        utilities=CoreUseCasesContainer.utilities,
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
