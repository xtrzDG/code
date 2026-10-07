from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.channels.staff_links import (
    PlatformBotWebhookOutcome,
    PlatformBotWebhookRequest,
)
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
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
from app.schemas.dto.inbox_sweep import InboundEventHandoffMark, UnansweredInboundEvent
from app.schemas.dto.jobs import JobTick, QueuedJobInput
from app.schemas.dto.media_requests import InboundMediaRequest
from app.schemas.dto.voice_webhooks import (
    FinishedCallReport,
    PostCallWebhookOutcome,
    PostCallWebhookRequest,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.channels.inbox.accept_platform_bot_update_use_case import (
    AcceptPlatformBotUpdateUseCase,
)
from app.use_cases.channels.inbox.claim_inbound_event_use_case import (
    ClaimInboundEventUseCase,
)
from app.use_cases.channels.inbox.collect_unanswered_inbound_events_use_case import (
    CollectUnansweredInboundEventsUseCase,
)
from app.use_cases.channels.inbox.fetch_inbound_media_use_case import (
    FetchInboundMediaUseCase,
)
from app.use_cases.channels.inbox.finish_inbound_event_use_case import (
    FinishInboundEventUseCase,
)
from app.use_cases.channels.inbox.mark_inbound_event_handed_off_use_case import (
    MarkInboundEventHandedOffUseCase,
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
from app.use_cases.channels.inbox.requeue_stale_inbound_events_use_case import (
    RequeueStaleInboundEventsUseCase,
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
from app.use_cases.widget.queue_widget_message_use_case import (
    QueueWidgetMessageUseCase,
)


class DeliveryUseCasesContainer(containers.DeclarativeContainer):
    """
    The inbox (webhooks acknowledged at once, messages processed by the
    worker) and the outbox (replies and staff notifications sent by the
    worker with retries).
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- The inbox: what webhooks store, each event and its job in one
    # transaction.
    store_inbound_messages_use_case: Factory[
        UseCaseContract[list[RoutedInboundMessage], InboxIntake]
    ] = Factory(
        StoreInboundMessagesUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        channel_repo=repositories.channel_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
        metrics=utilities.service_metrics,
    )
    accept_platform_bot_update_use_case: Factory[
        UseCaseContract[PlatformBotWebhookRequest, PlatformBotWebhookOutcome]
    ] = Factory(
        AcceptPlatformBotUpdateUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        app_settings=config.app_settings,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
    store_post_call_report_use_case: Factory[
        UseCaseContract[VerifiedPostCallReport, PostCallWebhookOutcome]
    ] = Factory(
        StorePostCallReportUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
    # The website widget's messages: into the inbox and queued in one
    # transaction; a worker answers them like every channel's.
    queue_widget_message_use_case: Factory[
        UseCaseContract[InboundMessage, WidgetMessageAcceptedView]
    ] = Factory(
        QueueWidgetMessageUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
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
        channel_repo=repositories.channel_repo,
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

    # --- The inbox's sweeper: lost jobs queued again, unanswered messages
    # handed to staff.
    requeue_stale_inbound_events_use_case: Factory[
        UseCaseContract[JobTick, ProcessedItemCount]
    ] = Factory(
        RequeueStaleInboundEventsUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        job_repo=repositories.queued_job_repo,
        job_queue=facilitators.job_queue_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    collect_unanswered_inbound_events_use_case: Factory[
        UseCaseContract[JobTick, list[UnansweredInboundEvent]]
    ] = Factory(
        CollectUnansweredInboundEventsUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        business_repo=repositories.business_repo,
        conversation_repo=repositories.conversation_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    mark_inbound_event_handed_off_use_case: Factory[
        UseCaseContract[InboundEventHandoffMark, InboundEventDocument | None]
    ] = Factory(
        MarkInboundEventHandedOffUseCase,
        inbound_event_repo=repositories.inbound_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
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
        push_sender=facilitators.push_notification_sender,
        usage_event_repo=repositories.usage_event_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        whatsapp_templates=adapters.whatsapp_channel_adapter,
        billing_attachments=facilitators.billing_email_attachments,
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
        delivery_recorder=facilitators.staff_delivery_recorder,
        feedback_request_repo=repositories.feedback_request_repo,
        metrics=utilities.service_metrics,
    )
    build_undelivered_reply_handoff_use_case: Factory[
        UseCaseContract[OutboundMessageDocument, HandoffCommand | None]
    ] = Factory(
        BuildUndeliveredReplyHandoffUseCase,
        business_repo=repositories.business_repo,
        conversation_repo=repositories.conversation_repo,
    )
    # Voice notes and photos of a customer message, read by the worker.
    fetch_inbound_media_use_case: Factory[
        UseCaseContract[InboundMediaRequest, list[MessageAttachment]]
    ] = Factory(
        FetchInboundMediaUseCase,
        channel_repo=repositories.channel_repo,
        secret_cipher=adapters.secret_cipher,
        media_fetcher=adapters.media.media_fetcher,
        media_storage=adapters.media.media_storage,
        message_media_repo=repositories.message_media_repo,
        media_settings=config.app_settings.provided.media,
        wall_clock=time_provider.microsecond_wall_clock,
    )
