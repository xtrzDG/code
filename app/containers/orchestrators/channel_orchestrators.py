from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.provider_chains import use_case_orchestrator
from app.containers.use_cases.channel_use_cases import ChannelUseCasesContainer


class ChannelOrchestratorsContainer(containers.DeclarativeContainer):
    """
    Orchestrators of messaging webhooks, the website widget, cabinet
    channel settings, staff links and the platform bot.
    """

    channel_use_cases: ChannelUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- Channels: webhooks, widget, cabinet settings, staff links.
    verify_meta_webhook_orchestrator = use_case_orchestrator(
        channel_use_cases.verify_meta_webhook_use_case
    )
    handle_platform_bot_update_orchestrator = use_case_orchestrator(
        channel_use_cases.handle_platform_bot_update_use_case
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
