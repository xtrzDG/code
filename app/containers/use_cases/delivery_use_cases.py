from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.channels.staff_links import (
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
)
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.deliveries import (
    InboundAnswer,
    InboundEventClaim,
    InboundFailure,
    InboxIntake,
    OutboundAttempt,
    RoutedInboundMessage,
    VerifiedPostCallReport,
)
from app.schemas.dto.handoffs import HandoffCommand
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
)
from app.use_cases.channels.inbox.accept_platform_bot_update_use_case import (
    AcceptPlatformBotUpdateUseCase,
)
from app.use_cases.channels.inbox.claim_inbound_event_use_case import (
    ClaimInboundEventUseCase,
)
from app.use_cases.channels.inbox.finish_inbound_event_use_case import (
    FinishInboundEventUseCase,
)
from app.use_cases.channels.inbox.open_widget_event_use_case import (
    OpenWidgetEventUseCase,
)
from app.use_cases.channels.inbox.read_accepted_post_call_use_case import (
    ReadAcceptedPostCallUseCase,
)
from app.use_cases.channels.inbox.recall_inbound_reply_use_case import (
    RecallInboundReplyUseCase,
)
from app.use_cases.channels.inbox.release_inbound_event_use_case import (
    ReleaseInboundEventUseCase,
)
from app.use_cases.channels.inbox.store_inbound_messages_use_case import (
    StoreInboundMessagesUseCase,
)
from app.use_cases.channels.inbox.store_post_call_report_use_case import (
    StorePostCallReportUseCase,
)
from app.use_cases.channels.outbox.build_undelivered_reply_handoff_use_case import (
    BuildUndeliveredReplyHandoffUseCase,
)
from app.use_cases.channels.outbox.record_outbound_attempt_use_case import (
    RecordOutboundAttemptUseCase,
)
from app.use_cases.channels.outbox.send_outbound_message_use_case import (
    SendOutboundMessageUseCase,
)
from app.use_cases.channels.outbox.take_due_outbound_message_use_case import (
    TakeDueOutboundMessageUseCase,
)


class DeliveryUseCasesContainer(containers.DeclarativeContainer):
    """
    The inbox (webhooks acknowledged at once, messages processed by the
    worker) and the outbox (replies and staff notifications sent by the
    worker with retries).
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- The inbox: what webhooks store.
    store_inbound_messages_use_case: Factory[
        UseCaseContract[list[RoutedInboundMessage], InboxIntake]
    ] = Factory(
        StoreInboundMessagesUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    accept_platform_bot_update_use_case: Factory[
        UseCaseContract[PlatformBotWebhookRequest, PlatformBotWebhookOutcome]
    ] = Factory(
        AcceptPlatformBotUpdateUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    store_post_call_report_use_case: Factory[
        UseCaseContract[VerifiedPostCallReport, PostCallWebhookOutcome]
    ] = Factory(
        StorePostCallReportUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    open_widget_event_use_case: Factory[
        UseCaseContract[InboundMessage, InboundEventClaim]
    ] = Factory(
        OpenWidgetEventUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- The inbox: what the worker does with an event.
    claim_inbound_event_use_case: Factory[
        UseCaseContract[QueuedJobInput, InboundEventClaim | None]
    ] = Factory(
        ClaimInboundEventUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    recall_inbound_reply_use_case: Factory[
        UseCaseContract[InboundEventDocument, InboundAnswer | None]
    ] = Factory(RecallInboundReplyUseCase, message_repo=repositories.message_repo)
    finish_inbound_event_use_case: Factory[
        UseCaseContract[InboundAnswer, InboundEventDocument | None]
    ] = Factory(
        FinishInboundEventUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    release_inbound_event_use_case: Factory[
        UseCaseContract[InboundFailure, InboundEventDocument | None]
    ] = Factory(
        ReleaseInboundEventUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    read_accepted_post_call_use_case: Factory[
        UseCaseContract[PostCallWebhookRequest, FinishedCallReport | None]
    ] = Factory(
        ReadAcceptedPostCallUseCase,
        voice_webhook_adapter=adapters.voice_webhook_adapter,
    )

    # --- The outbox.
    take_due_outbound_message_use_case: Factory[
        UseCaseContract[QueuedJobInput, OutboundMessageDocument | None]
    ] = Factory(
        TakeDueOutboundMessageUseCase,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_outbound_message_use_case: Factory[
        UseCaseContract[OutboundMessageDocument, OutboundAttempt]
    ] = Factory(
        SendOutboundMessageUseCase,
        telegram_adapter=adapters.telegram_channel_adapter,
        whatsapp_adapter=adapters.whatsapp_channel_adapter,
        messenger_adapter=adapters.messenger_channel_adapter,
        instagram_adapter=adapters.instagram_channel_adapter,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        staff_sender=facilitators.staff_notification_sender,
        usage_event_repo=repositories.usage_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_outbound_attempt_use_case: Factory[
        UseCaseContract[OutboundAttempt, OutboundMessageDocument | None]
    ] = Factory(
        RecordOutboundAttemptUseCase,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        channel_repo=repositories.channel_repo,
        handoff_repo=repositories.handoff_repo,
        live_events=facilitators.event_publisher,
    )
    build_undelivered_reply_handoff_use_case: Factory[
        UseCaseContract[OutboundMessageDocument, HandoffCommand | None]
    ] = Factory(
        BuildUndeliveredReplyHandoffUseCase,
        business_repo=repositories.business_repo,
        conversation_repo=repositories.conversation_repo,
    )
