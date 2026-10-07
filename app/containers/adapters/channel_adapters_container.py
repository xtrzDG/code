from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.utilities import UtilitiesContainer


class ChannelAdaptersContainer(containers.DeclarativeContainer):
    """
    The messaging channels: Telegram bots, the WhatsApp Cloud API (also the
    template sender of staff notifications), Messenger pages and Instagram
    accounts. Meta's channels show "typing…" through the typing client.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    telegram_channel_adapter: Singleton[TelegramChannelAdapter] = Singleton(
        TelegramChannelAdapter,
        telegram_client=clients.telegram_bot_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    whatsapp_channel_adapter: Singleton[WhatsAppChannelAdapter] = Singleton(
        WhatsAppChannelAdapter,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
        text_resolver=utilities.localized_text_resolver,
    )
    messenger_channel_adapter: Singleton[MessengerChannelAdapter] = Singleton(
        MessengerChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
    )
    instagram_channel_adapter: Singleton[InstagramChannelAdapter] = Singleton(
        InstagramChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
    )
