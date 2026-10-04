from dependency_injector import containers
from dependency_injector.providers import (
    DependenciesContainer,
    Dependency,
    Dict,
    Singleton,
)

from app.adapters.llm.media_resolving_llm_adapter import MediaResolvingLlmAdapter
from app.adapters.media.media_storage_factory import build_media_storage
from app.adapters.media.meta_page_media_fetcher_adapter import (
    MetaPageMediaFetcherAdapter,
)
from app.adapters.media.routing_channel_media_fetcher_adapter import (
    RoutingChannelMediaFetcherAdapter,
)
from app.adapters.media.telegram_media_fetcher_adapter import (
    TelegramMediaFetcherAdapter,
)
from app.adapters.media.voice_transcriber_factory import build_voice_transcriber
from app.adapters.media.whatsapp_media_fetcher_adapter import (
    WhatsAppMediaFetcherAdapter,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.contracts.channel_media import (
    ChannelMediaFetcherContract,
    VoiceTranscriberContract,
)
from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.constants.channels import ChannelKind


class MediaAdaptersContainer(containers.DeclarativeContainer):
    """
    The adapters of what customers send besides text: the encrypted storage
    of their voice notes and photos (beside call recordings), the file
    download of each messaging platform, the speech-to-text of voice notes,
    and the language model that is shown the stored photos (`llm_adapter`
    is the model it decorates).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    # The LlmAdapterContract it decorates (a Dependency checks no type).
    llm_adapter: Dependency[object] = Dependency()

    media_storage: Singleton[MediaStorageAdapterContract] = Singleton(
        build_media_storage,
        settings=config.app_settings,
        object_storage_client=clients.object_storage_client,
    )
    meta_page_media_fetcher: Singleton[MetaPageMediaFetcherAdapter] = Singleton(
        MetaPageMediaFetcherAdapter, meta_media_client=clients.meta_media_client
    )
    media_fetcher: Singleton[ChannelMediaFetcherContract] = Singleton(
        RoutingChannelMediaFetcherAdapter,
        fetchers=Dict(
            {
                ChannelKind.WHATSAPP: Singleton(
                    WhatsAppMediaFetcherAdapter,
                    meta_media_client=clients.meta_media_client,
                    app_settings=config.app_settings,
                ),
                ChannelKind.TELEGRAM: Singleton(
                    TelegramMediaFetcherAdapter,
                    telegram_file_client=clients.telegram_file_client,
                ),
                ChannelKind.MESSENGER: meta_page_media_fetcher,
                ChannelKind.INSTAGRAM: meta_page_media_fetcher,
            }
        ),
    )
    voice_transcriber: Singleton[VoiceTranscriberContract] = Singleton(
        build_voice_transcriber,
        settings=config.app_settings,
        client=clients.openai_transcription_client,
    )
    # Photos customers sent, read from the storage for every request.
    media_llm_adapter: Singleton[MediaResolvingLlmAdapter] = Singleton(
        MediaResolvingLlmAdapter, inner_adapter=llm_adapter, media_storage=media_storage
    )
