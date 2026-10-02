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
from app.contracts.orchestrator_contract import OrchestratorContract
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.orchestrators.channels.widget_message_orchestrator import (
    WidgetMessageOrchestrator,
)
from app.schemas.dto.channels.channel_webhooks import (
    ChannelWebhookOutcome,
    MetaWebhookRequest,
    TelegramWebhookRequest,
)
from app.schemas.dto.channels.widget import WidgetMessageCommand, WidgetReplyView


class ChannelPipelinesContainer(containers.DeclarativeContainer):
    """
    Pipelines of messaging webhooks, the website widget, cabinet channel
    settings, staff links and the platform bot.
    """

    channel_orchestrators: ChannelOrchestratorsContainer = DependenciesContainer()  # type: ignore[assignment]
    channel_use_cases: ChannelUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    conversation_pipelines: ConversationPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Messaging webhooks and the website widget.
    telegram_webhook_orchestrator: Factory[
        OrchestratorContract[TelegramWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[TelegramWebhookRequest],
        receive_webhook=channel_use_cases.receive_telegram_webhook_use_case,
        customer_message_pipeline=conversation_pipelines.customer_message_pipeline,
        deliver_reply=channel_use_cases.deliver_channel_reply_use_case,
    )
    meta_webhook_orchestrator: Factory[
        OrchestratorContract[MetaWebhookRequest, ChannelWebhookOutcome]
    ] = Factory(
        ChannelWebhookOrchestrator[MetaWebhookRequest],
        receive_webhook=channel_use_cases.receive_meta_webhook_use_case,
        customer_message_pipeline=conversation_pipelines.customer_message_pipeline,
        deliver_reply=channel_use_cases.deliver_channel_reply_use_case,
    )
    widget_message_orchestrator: Factory[
        OrchestratorContract[WidgetMessageCommand, WidgetReplyView]
    ] = Factory(
        WidgetMessageOrchestrator,
        accept_widget_message=channel_use_cases.accept_widget_message_use_case,
        customer_message_pipeline=conversation_pipelines.customer_message_pipeline,
        build_widget_reply=channel_use_cases.build_widget_reply_use_case,
    )
    telegram_webhook_pipeline = orchestrator_pipeline(telegram_webhook_orchestrator)
    meta_webhook_pipeline = orchestrator_pipeline(meta_webhook_orchestrator)
    widget_message_pipeline = orchestrator_pipeline(widget_message_orchestrator)

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_pipeline = orchestrator_pipeline(
        channel_orchestrators.verify_meta_webhook_orchestrator
    )
    handle_platform_bot_update_pipeline = orchestrator_pipeline(
        channel_orchestrators.handle_platform_bot_update_orchestrator
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
