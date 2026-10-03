from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.orchestrators.channel_orchestrators import (
    ChannelOrchestratorsContainer,
)
from app.containers.pipelines.conversation_pipelines import (
    ConversationPipelinesContainer,
)
from app.containers.provider_chains import orchestrator_pipeline
from app.containers.use_cases.channel_use_cases import ChannelUseCasesContainer
from app.containers.use_cases.delivery_use_cases import DeliveryUseCasesContainer
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.orchestrators.channels.inbox.process_inbound_message_orchestrator import (
    ProcessInboundMessageOrchestrator,
)
from app.orchestrators.channels.widget_message_orchestrator import (
    WidgetMessageOrchestrator,
)
from app.schemas.dto.channels.channel_webhooks import (
    ChannelWebhookOutcome,
    MetaWebhookRequest,
    TelegramWebhookRequest,
)
from app.schemas.dto.channels.widget import WidgetMessageCommand
from app.schemas.dto.channels.widget_turns import WidgetMessageAcceptedView
from app.schemas.dto.jobs import JobReport, QueuedJobInput


class ChannelPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of messaging webhooks, the website widget, cabinet channel
    settings, staff links and the platform bot.
    """

    channel_orchestrators: ChannelOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
    channel_use_cases: ChannelUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    delivery_use_cases: DeliveryUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_pipelines: ConversationPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Messaging webhooks and the website widget: webhooks store their
    # messages in the inbox; the worker answers them through the pipeline.
    telegram_webhook_orchestrator: Factory[
        OrchestratorContract[TelegramWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[TelegramWebhookRequest],
        receive_webhook=channel_use_cases.receive_telegram_webhook_use_case,
        store_inbound_messages=delivery_use_cases.store_inbound_messages_use_case,
    )
    meta_webhook_orchestrator: Factory[
        OrchestratorContract[MetaWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[MetaWebhookRequest],
        receive_webhook=channel_use_cases.receive_meta_webhook_use_case,
        store_inbound_messages=delivery_use_cases.store_inbound_messages_use_case,
    )
    widget_message_orchestrator: Factory[
        OrchestratorContract[WidgetMessageCommand, WidgetMessageAcceptedView]
    ] = Factory(
        WidgetMessageOrchestrator,
        accept_widget_message=channel_use_cases.accept_widget_message_use_case,
        queue_widget_message=delivery_use_cases.queue_widget_message_use_case,
    )
    process_inbound_message_orchestrator: Factory[
        OrchestratorContract[QueuedJobInput, JobReport]
    ] = Factory(
        ProcessInboundMessageOrchestrator,
        claim_inbound_event=delivery_use_cases.claim_inbound_event_use_case,
        recall_inbound_reply=delivery_use_cases.recall_inbound_reply_use_case,
        customer_message_pipeline=conversation_pipelines.customer_message_pipeline,
        finish_inbound_event=delivery_use_cases.finish_inbound_event_use_case,
        release_inbound_event=delivery_use_cases.release_inbound_event_use_case,
    )
    telegram_webhook_pipeline = orchestrator_pipeline(telegram_webhook_orchestrator)
    meta_webhook_pipeline = orchestrator_pipeline(meta_webhook_orchestrator)
    widget_message_pipeline = orchestrator_pipeline(widget_message_orchestrator)
    process_inbound_message_pipeline = orchestrator_pipeline(
        process_inbound_message_orchestrator
    )

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_pipeline = orchestrator_pipeline(
        channel_orchestrators.verify_meta_webhook_orchestrator
    )
    handle_platform_bot_update_pipeline = orchestrator_pipeline(
        channel_orchestrators.handle_platform_bot_update_orchestrator
    )
    process_platform_bot_update_pipeline = orchestrator_pipeline(
        channel_orchestrators.process_platform_bot_update_orchestrator
    )
    deliver_outbound_pipeline = orchestrator_pipeline(
        channel_orchestrators.deliver_outbound_orchestrator
    )
    get_widget_config_pipeline = orchestrator_pipeline(
        channel_orchestrators.get_widget_config_orchestrator
    )
    get_widget_messages_pipeline = orchestrator_pipeline(
        channel_orchestrators.get_widget_messages_orchestrator
    )
    list_channels_pipeline = orchestrator_pipeline(
        channel_orchestrators.list_channels_orchestrator
    )
    connect_channel_pipeline = orchestrator_pipeline(
        channel_orchestrators.connect_channel_orchestrator
    )
    disable_channel_pipeline = orchestrator_pipeline(
        channel_orchestrators.disable_channel_orchestrator
    )
    set_whatsapp_staff_template_pipeline = orchestrator_pipeline(
        channel_orchestrators.set_whatsapp_staff_template_orchestrator
    )
    get_widget_snippet_pipeline = orchestrator_pipeline(
        channel_orchestrators.get_widget_snippet_orchestrator
    )
    create_telegram_link_pipeline = orchestrator_pipeline(
        channel_orchestrators.create_telegram_link_orchestrator
    )
    configure_platform_bot_webhook_pipeline = orchestrator_pipeline(
        channel_orchestrators.configure_platform_bot_webhook_orchestrator
    )
