from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.pipelines.channel_pipelines import ChannelPipelinesContainer
from app.containers.provider_chains import (
    pipeline_operator,
    platform_pipeline_operator,
)
from app.containers.utilities import UtilitiesContainer


class ChannelOperatorsContainer(containers.DeclarativeContainer):
    """
    Operators of messaging webhooks, the website widget, cabinet channel
    settings, staff links and the platform bot.
    """

    channel_pipelines: ChannelPipelinesContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # Operators run inside the storage scope of the business they serve;
    # platform_pipeline_operator marks platform-level work (platform-wide).
    storage_scope = utilities.storage_scope

    # --- Messaging webhooks and the website widget.
    telegram_webhook_operator = platform_pipeline_operator(
        channel_pipelines.telegram_webhook_pipeline, storage_scope
    )
    meta_webhook_operator = platform_pipeline_operator(
        channel_pipelines.meta_webhook_pipeline, storage_scope
    )
    widget_message_operator = pipeline_operator(
        channel_pipelines.widget_message_pipeline, storage_scope
    )

    # --- Worker jobs: the inbox and the outbox.
    process_inbound_message_operator = pipeline_operator(
        channel_pipelines.process_inbound_message_pipeline, storage_scope
    )
    process_platform_bot_update_operator = platform_pipeline_operator(
        channel_pipelines.process_platform_bot_update_pipeline, storage_scope
    )
    deliver_outbound_operator = pipeline_operator(
        channel_pipelines.deliver_outbound_pipeline, storage_scope
    )
    # The inbox's sweeper reads every business's events: platform-wide.
    sweep_stale_inbound_events_operator = platform_pipeline_operator(
        channel_pipelines.sweep_stale_inbound_events_pipeline, storage_scope
    )

    # --- Channels: webhook checks, widget, cabinet settings, staff links.
    verify_meta_webhook_operator = pipeline_operator(
        channel_pipelines.verify_meta_webhook_pipeline, storage_scope
    )
    handle_platform_bot_update_operator = platform_pipeline_operator(
        channel_pipelines.handle_platform_bot_update_pipeline, storage_scope
    )
    get_widget_config_operator = pipeline_operator(
        channel_pipelines.get_widget_config_pipeline, storage_scope
    )
    get_widget_messages_operator = pipeline_operator(
        channel_pipelines.get_widget_messages_pipeline, storage_scope
    )
    list_channels_operator = pipeline_operator(
        channel_pipelines.list_channels_pipeline, storage_scope
    )
    connect_channel_operator = pipeline_operator(
        channel_pipelines.connect_channel_pipeline, storage_scope
    )
    disable_channel_operator = pipeline_operator(
        channel_pipelines.disable_channel_pipeline, storage_scope
    )
    set_whatsapp_staff_template_operator = pipeline_operator(
        channel_pipelines.set_whatsapp_staff_template_pipeline, storage_scope
    )
    set_whatsapp_staff_templates_operator = pipeline_operator(
        channel_pipelines.set_whatsapp_staff_templates_pipeline, storage_scope
    )
    validate_telegram_token_operator = pipeline_operator(
        channel_pipelines.validate_telegram_token_pipeline, storage_scope
    )
    get_widget_snippet_operator = pipeline_operator(
        channel_pipelines.get_widget_snippet_pipeline, storage_scope
    )
    create_telegram_link_operator = pipeline_operator(
        channel_pipelines.create_telegram_link_pipeline, storage_scope
    )
    configure_platform_bot_webhook_operator = pipeline_operator(
        channel_pipelines.configure_platform_bot_webhook_pipeline, storage_scope
    )
