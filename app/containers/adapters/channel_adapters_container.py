from dependency_injector import containers
from dependency_injector.providers import (
    DependenciesContainer,
    Dependency,
    Object,
    Singleton,
)

from app.adapters.channels.circuit_breaking_channel_adapter import (
    CircuitBreakingChannelAdapter,
)
from app.adapters.channels.circuit_breaking_whatsapp_template_adapter import (
    CircuitBreakingWhatsAppTemplateAdapter,
)
from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.utilities import UtilitiesContainer
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import OutboundProvider
from app.utilities.resilience.provider_circuits import provider_circuit


class ChannelAdaptersContainer(containers.DeclarativeContainer):
    """
    The messaging channels: Telegram bots, the WhatsApp Cloud API (also the
    template sender of staff notifications), Messenger pages and Instagram
    accounts. Meta's channels show "typing…" through the typing client.

    Every channel sends behind its provider's circuit breaker (`provider:
    meta` for WhatsApp, Messenger and Instagram, `provider:telegram` for
    the businesses' bots): an open circuit refuses a send at once instead
    of waiting for the provider's timeout.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    # The process's one circuit breaker (AdaptersContainer.resilience).
    circuit_breaker: Dependency[CircuitBreakerFacilitator] = Dependency(
        instance_of=CircuitBreakerFacilitator
    )

    telegram_bots: Singleton[TelegramChannelAdapter] = Singleton(
        TelegramChannelAdapter,
        telegram_client=clients.telegram_bot_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    whatsapp_cloud: Singleton[WhatsAppChannelAdapter] = Singleton(
        WhatsAppChannelAdapter,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
        text_resolver=utilities.localized_text_resolver,
    )
    messenger_pages: Singleton[MessengerChannelAdapter] = Singleton(
        MessengerChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
    )
    instagram_accounts: Singleton[InstagramChannelAdapter] = Singleton(
        InstagramChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
        typing_client=clients.meta_typing_client,
        private_reply_client=clients.meta_private_reply_client,
    )

    # --- The channels as the rest of the application gets them.
    meta_circuit = Object(provider_circuit(OutboundProvider.META))
    telegram_channel_adapter: Singleton[CircuitBreakingChannelAdapter] = Singleton(
        CircuitBreakingChannelAdapter,
        inner_adapter=telegram_bots,
        circuit_breaker=circuit_breaker,
        circuit=Object(provider_circuit(OutboundProvider.TELEGRAM)),
    )
    whatsapp_channel_adapter: Singleton[CircuitBreakingChannelAdapter] = Singleton(
        CircuitBreakingChannelAdapter,
        inner_adapter=whatsapp_cloud,
        circuit_breaker=circuit_breaker,
        circuit=meta_circuit,
    )
    # WhatsApp templates (customers outside the 24-hour window, staff).
    whatsapp_template_sender: Singleton[CircuitBreakingWhatsAppTemplateAdapter] = (
        Singleton(
            CircuitBreakingWhatsAppTemplateAdapter,
            inner_adapter=whatsapp_cloud,
            circuit_breaker=circuit_breaker,
            circuit=meta_circuit,
        )
    )
    messenger_channel_adapter: Singleton[CircuitBreakingChannelAdapter] = Singleton(
        CircuitBreakingChannelAdapter,
        inner_adapter=messenger_pages,
        circuit_breaker=circuit_breaker,
        circuit=meta_circuit,
    )
    instagram_channel_adapter: Singleton[CircuitBreakingChannelAdapter] = Singleton(
        CircuitBreakingChannelAdapter,
        inner_adapter=instagram_accounts,
        circuit_breaker=circuit_breaker,
        circuit=meta_circuit,
    )
