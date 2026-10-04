from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.channel_use_cases import ChannelUseCasesContainer
from app.containers.use_cases.conversation_use_cases import (
    ConversationUseCasesContainer,
)
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.inbox.process_platform_bot_update_orchestrator import (
    ProcessPlatformBotUpdateOrchestrator,
)
from app.orchestrators.channels.inbox.read_inbound_attachments_orchestrator import (
    ReadInboundAttachmentsOrchestrator,
)
from app.orchestrators.channels.outbox.deliver_outbound_message_orchestrator import (
    DeliverOutboundMessageOrchestrator,
)
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.media_requests import InboundMediaRequest


class ChannelOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of messaging webhooks, the website widget, cabinet
    channel settings, staff links, the platform bot and the outbox.
    """

    channel_use_cases: ChannelUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    delivery_use_cases: DeliveryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_use_cases: ConversationUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Voice notes and photos of a customer message, read by the worker.
    read_inbound_attachments_orchestrator: Factory[
        OrchestratorContract[InboundMediaRequest, InboundMessage]
    ] = Factory(
        ReadInboundAttachmentsOrchestrator,
        fetch_inbound_media=delivery_use_cases.fetch_inbound_media_use_case,
        transcribe_voice_note=conversation_use_cases.transcribe_voice_note_use_case,
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_orchestrator = use_case_orchestrator(
        channel_use_cases.verify_meta_webhook_use_case
    )
    # The platform bot's webhook only stores the update; the worker answers.
    handle_platform_bot_update_orchestrator = use_case_orchestrator(
        delivery_use_cases.accept_platform_bot_update_use_case
    )
    get_widget_config_orchestrator = use_case_orchestrator(
        channel_use_cases.get_widget_config_use_case
    )
    get_widget_messages_orchestrator = use_case_orchestrator(
        channel_use_cases.get_widget_messages_use_case
    )
    list_channels_orchestrator = use_case_orchestrator(
        channel_use_cases.list_channels_use_case
    )
    connect_channel_orchestrator = use_case_orchestrator(
        channel_use_cases.connect_channel_use_case
    )
    disable_channel_orchestrator = use_case_orchestrator(
        channel_use_cases.disable_channel_use_case
    )
    set_whatsapp_staff_template_orchestrator = use_case_orchestrator(
        channel_use_cases.set_whatsapp_staff_template_use_case
    )
    get_widget_snippet_orchestrator = use_case_orchestrator(
        channel_use_cases.get_widget_snippet_use_case
    )
    create_telegram_link_orchestrator = use_case_orchestrator(
        channel_use_cases.create_telegram_link_use_case
    )
    configure_platform_bot_webhook_orchestrator = use_case_orchestrator(
        channel_use_cases.configure_platform_bot_webhook_use_case
    )

    # --- Worker jobs: the platform bot's updates and the outbox.
    process_platform_bot_update_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        ProcessPlatformBotUpdateOrchestrator,
        claim_inbound_event=delivery_use_cases.claim_inbound_event_use_case,
        handle_platform_bot_update=channel_use_cases.handle_platform_bot_update_use_case,
        finish_inbound_event=delivery_use_cases.finish_inbound_event_use_case,
        release_inbound_event=delivery_use_cases.release_inbound_event_use_case,
    )
    deliver_outbound_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        DeliverOutboundMessageOrchestrator,
        take_due_outbound_message=delivery_use_cases.take_due_outbound_message_use_case,
        send_outbound_message=delivery_use_cases.send_outbound_message_use_case,
        record_outbound_attempt=delivery_use_cases.record_outbound_attempt_use_case,
        build_undelivered_reply_handoff=(
            delivery_use_cases.build_undelivered_reply_handoff_use_case
        ),
        handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
    )
