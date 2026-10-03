from dependency_injector import containers
from dependency_injector.providers import (
    Callable,
    Container,
    DependenciesContainer,
    Singleton,
)

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.events.live_event_bus_factory import build_live_event_bus_adapter
from app.adapters.health.database_probe_factory import build_database_probe_adapter
from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.adapters.llm.call_limited_llm_adapter import (
    CHAT_CALL_RETRY_LIMIT,
    CallLimitedLlmAdapter,
)
from app.adapters.llm.menu_extraction.menu_extraction_adapter import (
    MenuExtractionAdapter,
)
from app.adapters.llm.offline_llm_adapter import OfflineLlmAdapter
from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.recordings.cached_recording_storage_adapter import (
    CachedRecordingStorageAdapter,
)
from app.adapters.recordings.local_recording_storage_adapter import (
    LocalRecordingStorageAdapter,
)
from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    BUILD_MIGRATIONS_DIRECTORY,
    SqlFileMigrationSourceAdapter,
)
from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.adapters.voice.elevenlabs_voice_agent_provisioner import (
    ElevenLabsVoiceAgentProvisioner,
)
from app.adapters.voice.elevenlabs_voice_webhook_adapter import (
    ElevenLabsVoiceWebhookAdapter,
)
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import (
    build_llm_trace_facilitator,
    resolve_recordings_directory,
    select_menu_extraction_model_id,
)
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.health import DatabaseProbeAdapterContract
from app.contracts.live_events import LiveEventBusAdapterContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.schemas.dto.conversations import LlmCallLimits


class AdaptersContainer(containers.DeclarativeContainer):
    """
    Adapters: the document collections (a child container the repositories
    are built on) and the adapters of external services - security,
    recordings, the voice platform, messaging channels, language models and
    payments.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # Document collections: Postgres with DATABASE_URL, else in memory.
    collections: DocumentCollectionsContainer = Container(  # type: ignore[assignment]
        DocumentCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )

    # --- Readiness (GET /readyz): the database probe over the shared pool and
    # the migration files of this build.
    database_probe: Singleton[DatabaseProbeAdapterContract] = Singleton(
        build_database_probe_adapter,
        connection_pool=clients.postgres_pool,
    )
    migration_source: Singleton[SqlFileMigrationSourceAdapter] = Singleton(
        SqlFileMigrationSourceAdapter,
        migrations_directory=BUILD_MIGRATIONS_DIRECTORY,
    )

    # --- The cabinet's live updates between processes: Postgres
    # NOTIFY/LISTEN with DATABASE_URL, else in this process.
    live_event_bus: Singleton[LiveEventBusAdapterContract] = Singleton(
        build_live_event_bus_adapter,
        connection_pool=clients.postgres_pool,
        database_url=config.app_settings.provided.database_url,
        listen_database_url=config.app_settings.provided.live_events_database_url,
    )

    # --- Security and recordings.
    secret_cipher: Singleton[SecretCipherAdapter] = Singleton(
        SecretCipherAdapter,
        app_settings=config.app_settings,
    )
    local_recording_storage: Singleton[LocalRecordingStorageAdapter] = Singleton(
        LocalRecordingStorageAdapter,
        root_directory=Callable(
            resolve_recordings_directory,
            settings=config.app_settings,
        ),
    )
    # ElevenLabs keeps call audio in its own (EU) storage; other paths are
    # files of this server.
    platform_recording_storage: Singleton[ElevenLabsRecordingStorageAdapter] = (
        Singleton(
            ElevenLabsRecordingStorageAdapter,
            elevenlabs_client=clients.elevenlabs_client,
            fallback=local_recording_storage,
        )
    )
    # A player asks for parts of a recording while it plays and seeks: keep
    # a played one in memory for a few minutes instead of downloading it again.
    recording_storage: Singleton[CachedRecordingStorageAdapter] = Singleton(
        CachedRecordingStorageAdapter,
        storage=platform_recording_storage,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    # --- Voice platform (ElevenLabs Agents).
    voice_webhook_adapter: Singleton[ElevenLabsVoiceWebhookAdapter] = Singleton(
        ElevenLabsVoiceWebhookAdapter,
        app_settings=config.app_settings,
    )
    voice_agent_provisioner: Singleton[ElevenLabsVoiceAgentProvisioner] = Singleton(
        ElevenLabsVoiceAgentProvisioner,
        elevenlabs_client=clients.elevenlabs_client,
        app_settings=config.app_settings,
    )

    # --- Messaging channels.
    telegram_channel_adapter: Singleton[TelegramChannelAdapter] = Singleton(
        TelegramChannelAdapter,
        telegram_client=clients.telegram_bot_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    # Also the WhatsApp template sender (staff notifications).
    whatsapp_channel_adapter: Singleton[WhatsAppChannelAdapter] = Singleton(
        WhatsAppChannelAdapter,
        meta_client=clients.meta_graph_client,
        phone_number_parser=utilities.phone_number_parser,
        app_settings=config.app_settings,
    )
    messenger_channel_adapter: Singleton[MessengerChannelAdapter] = Singleton(
        MessengerChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
    )
    instagram_channel_adapter: Singleton[InstagramChannelAdapter] = Singleton(
        InstagramChannelAdapter,
        meta_client=clients.meta_graph_client,
        app_settings=config.app_settings,
    )

    # --- Language models.
    openai_llm_adapter: Singleton[OpenAiLlmAdapter] = Singleton(
        OpenAiLlmAdapter,
        client=clients.openai_responses_client,
    )
    anthropic_llm_adapter: Singleton[AnthropicLlmAdapter] = Singleton(
        AnthropicLlmAdapter,
        client=clients.anthropic_messages_client,
    )
    # LLM_PROVIDER=scripted (staging, offline runs): fixed answers, no network.
    offline_llm_adapter: Singleton[OfflineLlmAdapter] = Singleton(
        OfflineLlmAdapter,
        latency_ms=config.app_settings.provided.scripted_llm_latency_ms,
    )
    # Typed by its contract: tests replace it with the scripted model.
    routing_llm_adapter: Singleton[LlmAdapterContract] = Singleton(
        RoutingLlmAdapter,
        openai_adapter=openai_llm_adapter,
        anthropic_adapter=anthropic_llm_adapter,
        scripted_adapter=offline_llm_adapter,
    )
    # The quality journal (Langfuse, or nothing without keys). It lives here,
    # not in FacilitatorsContainer, because the LLM adapter below decorates
    # every model call with it and facilitators already depend on adapters.
    llm_trace_facilitator: Singleton[LlmTraceFacilitatorContract] = Singleton(
        build_llm_trace_facilitator,
        langfuse_client=clients.langfuse_ingestion_client,
    )
    # The adapter every use case gets: routing by model id, traced.
    llm_adapter: Singleton[TracingLlmAdapter] = Singleton(
        TracingLlmAdapter,
        inner_adapter=routing_llm_adapter,
        trace_facilitator=llm_trace_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        monotonic_clock=time_provider.monotonic_clock,
        is_content_traced=config.app_settings.provided.is_llm_content_traced,
    )
    # The adapter of a customer chat: each call bounded by
    # LLM_CALL_TIMEOUT_SECONDS and retried once.
    chat_llm_adapter: Singleton[CallLimitedLlmAdapter] = Singleton(
        CallLimitedLlmAdapter,
        inner_adapter=llm_adapter,
        limits=Singleton(
            LlmCallLimits,
            timeout_seconds=config.app_settings.provided.llm_call_timeout_seconds,
            retry_limit=CHAT_CALL_RETRY_LIMIT,
        ),
    )
    menu_extraction_adapter: Singleton[MenuExtractionAdapter] = Singleton(
        MenuExtractionAdapter,
        client=clients.openai_responses_client,
        model_id=Callable(
            select_menu_extraction_model_id,
            settings=config.app_settings,
        ),
    )

    # --- Payments.
    payment_gateway: Singleton[FlittPaymentGatewayAdapter] = Singleton(
        FlittPaymentGatewayAdapter,
        flitt_client=clients.flitt_client,
        app_base_url=config.app_settings.provided.app_base_url,
    )
