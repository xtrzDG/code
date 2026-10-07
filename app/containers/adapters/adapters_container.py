from dependency_injector import containers
from dependency_injector.providers import (
    Callable,
    Container,
    DependenciesContainer,
    Singleton,
)

from app.adapters.documents.weasyprint_invoice_document_renderer_adapter import (
    WeasyPrintInvoiceDocumentRendererAdapter,
)
from app.adapters.events.live_event_bus_factory import build_live_event_bus_adapter
from app.adapters.llm.anthropic_llm_adapter import AnthropicLlmAdapter
from app.adapters.llm.call_limited_llm_adapter import (
    CHAT_CALL_RETRY_LIMIT,
    CallLimitedLlmAdapter,
)
from app.adapters.llm.concurrency_limited_llm_adapter import (
    ConcurrencyLimitedLlmAdapter,
)
from app.adapters.llm.menu_extraction.menu_extraction_adapter import (
    MenuExtractionAdapter,
)
from app.adapters.llm.offline_llm_adapter import OfflineLlmAdapter
from app.adapters.llm.openai_llm_adapter import OpenAiLlmAdapter
from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.tracing_llm_adapter import TracingLlmAdapter
from app.adapters.locks.advisory_lock_adapter_factory import (
    build_advisory_lock_adapter,
)
from app.adapters.payments.flitt_payment_gateway_adapter import (
    FlittPaymentGatewayAdapter,
)
from app.adapters.rate_limits.rate_limit_bucket_adapter_factory import (
    build_rate_limit_bucket_adapter,
)
from app.containers.adapters.calendar_sync_collections_container import (
    CalendarSyncCollectionsContainer,
)
from app.containers.adapters.call_adapters_container import CallAdaptersContainer
from app.containers.adapters.channel_adapters_container import (
    ChannelAdaptersContainer,
)
from app.containers.adapters.document_collections_container import (
    DocumentCollectionsContainer,
)
from app.containers.adapters.file_storage_adapters_container import (
    FileStorageAdaptersContainer,
)
from app.containers.adapters.growth_collections_container import (
    GrowthCollectionsContainer,
)
from app.containers.adapters.launch_collections_container import (
    LaunchCollectionsContainer,
)
from app.containers.adapters.media_adapters_container import MediaAdaptersContainer
from app.containers.adapters.monitoring_adapters_container import (
    MonitoringAdaptersContainer,
)
from app.containers.adapters.notification_collections_container import (
    NotificationCollectionsContainer,
)
from app.containers.adapters.process_adapters_container import (
    ProcessAdaptersContainer,
)
from app.containers.adapters.security_adapters_container import (
    SecurityAdaptersContainer,
)
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.factories import (
    build_llm_trace_facilitator,
    select_menu_extraction_model_id,
)
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.live_events import LiveEventBusAdapterContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.dto.conversations import LlmCallLimits


class AdaptersContainer(containers.DeclarativeContainer):
    """
    Adapters: the document collections and the adapters of external services
    (security, recordings, voice, channels, customer media, models, payments).
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
    notification_collections: NotificationCollectionsContainer = Container(  # type: ignore[assignment]
        NotificationCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    launch_collections: LaunchCollectionsContainer = Container(  # type: ignore[assignment]
        LaunchCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # The waitlist and the rebooking campaigns (1151).
    growth_collections: GrowthCollectionsContainer = Container(  # type: ignore[assignment]
        GrowthCollectionsContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
        utilities=utilities,
    )
    # Two-way availability: calendar settings, busy times, export feeds (1160).
    calendar_sync_collections: CalendarSyncCollectionsContainer = Container(  # type: ignore[assignment]
        CalendarSyncCollectionsContainer, clients=clients, config=config,
        time_provider=time_provider, utilities=utilities,
    )  # fmt: skip
    calls: CallAdaptersContainer = Container(  # type: ignore[assignment]
        CallAdaptersContainer, clients=clients, config=config,
        time_provider=time_provider, utilities=utilities,
    )  # fmt: skip

    # Readiness, storage transactions and the job queue's wake-ups.
    processes: ProcessAdaptersContainer = Container(  # type: ignore[assignment]
        ProcessAdaptersContainer, clients=clients, config=config,
        time_provider=time_provider, utilities=utilities,
    )  # fmt: skip
    database_probe = processes.database_probe
    migration_source = processes.migration_source
    storage_unit_of_work = processes.storage_unit_of_work
    storage_read_session = processes.storage_read_session
    job_wakeup, data_task_batches = processes.job_wakeup, processes.data_task_batches
    # Locks every process respects (Postgres advisory locks over the shared
    # pool; in-process locks without a database).
    advisory_locks: Singleton[AdvisoryLockAdapterContract] = Singleton(
        build_advisory_lock_adapter,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
    )
    # Request counters of the rate limits (Postgres: shared by every
    # instance; in memory without a database).
    rate_limit_buckets: Singleton[RateLimitBucketAdapterContract] = Singleton(
        build_rate_limit_bucket_adapter,
        connection_pool=clients.postgres_pool,
    )

    # --- The cabinet's live updates between processes: Postgres
    # NOTIFY/LISTEN with DATABASE_URL, else in this process.
    live_event_bus: Singleton[LiveEventBusAdapterContract] = Singleton(
        build_live_event_bus_adapter,
        connection_pool=clients.postgres_pool,
        database_url=config.app_settings.provided.database_url,
        listen_database_url=config.app_settings.provided.live_events_database_url,
    )

    # --- Security (secrets sealed with the key ring) and recordings.
    security: SecurityAdaptersContainer = Container(  # type: ignore[assignment]
        SecurityAdaptersContainer, config=config
    )
    secret_cipher = security.secret_cipher
    totp_secret_cipher = security.totp_secret_cipher
    # Call recordings and the archives of full business exports.
    files: FileStorageAdaptersContainer = Container(  # type: ignore[assignment]
        FileStorageAdaptersContainer,
        clients=clients,
        config=config,
        time_provider=time_provider,
    )
    own_recording_storage = files.own_recording_storage
    platform_recording_storage = files.platform_recording_storage
    recording_storage = files.recording_storage
    export_archive_storage = files.export_archive_storage

    # --- Voice platform (ElevenLabs Agents), built with the call adapters.
    voice_webhook_adapter = calls.voice_webhook_adapter
    voice_agent_provisioner = calls.voice_agent_provisioner

    # --- Messaging channels.
    channels: ChannelAdaptersContainer = Container(  # type: ignore[assignment]
        ChannelAdaptersContainer, clients=clients, config=config, utilities=utilities
    )
    telegram_channel_adapter = channels.telegram_channel_adapter
    # Also the WhatsApp template sender (staff notifications).
    whatsapp_channel_adapter = channels.whatsapp_channel_adapter
    messenger_channel_adapter = channels.messenger_channel_adapter
    instagram_channel_adapter = channels.instagram_channel_adapter

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
        circuit_breaker=Singleton(
            CircuitBreakerFacilitator,
            monotonic_clock=time_provider.monotonic_clock,
            metrics=utilities.service_metrics,
        ),
        scripted_adapter=offline_llm_adapter,
        fallback_model_id=config.app_settings.provided.reply_speed.llm_fallback_model_id,
    )
    # The quality journal (Langfuse, or nothing without keys). It lives here,
    # not in FacilitatorsContainer, because the LLM adapter below decorates
    # every model call with it and facilitators already depend on adapters.
    llm_trace_facilitator: Singleton[LlmTraceFacilitatorContract] = Singleton(
        build_llm_trace_facilitator,
        langfuse_client=clients.langfuse_ingestion_client,
    )
    # Customer media: storage, downloads, speech-to-text, photos for models.
    media: MediaAdaptersContainer = Container(  # type: ignore[assignment]
        MediaAdaptersContainer, clients=clients, config=config,
        llm_adapter=routing_llm_adapter,
    )  # fmt: skip
    # Every model call traced (Langfuse) ...
    traced_llm_adapter: Singleton[TracingLlmAdapter] = Singleton(
        TracingLlmAdapter,
        inner_adapter=media.media_llm_adapter,
        trace_facilitator=llm_trace_facilitator,
        wall_clock=time_provider.microsecond_wall_clock,
        monotonic_clock=time_provider.monotonic_clock,
        is_content_traced=config.app_settings.provided.is_llm_content_traced,
        is_raw_text_traced=config.app_settings.provided.is_llm_raw_text_traced,
    )
    # Signal counters of the platform alerts; every model call counted.
    monitoring: MonitoringAdaptersContainer = Container(  # type: ignore[assignment]
        MonitoringAdaptersContainer, clients=clients, time_provider=time_provider,
        rate_limit_buckets=rate_limit_buckets, traced_llm_adapter=traced_llm_adapter,
        utilities=utilities,
    )  # fmt: skip
    signal_counter, database_size = monitoring.signal_counter, monitoring.database_size
    # ... and the adapter every use case gets: routing by model id, traced,
    # counted, at most LLM_MAX_CONCURRENCY calls of this process at once.
    llm_adapter: Singleton[ConcurrencyLimitedLlmAdapter] = Singleton(
        ConcurrencyLimitedLlmAdapter,
        inner_adapter=monitoring.counted_llm_adapter,
        max_concurrency=config.app_settings.provided.llm_max_concurrency,
        wait_seconds=config.app_settings.provided.llm_call_timeout_seconds,
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
        page_fetcher=clients.safe_http_fetcher,
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
    # Invoice and receipt PDFs (WeasyPrint, the system's Noto fonts).
    invoice_document_renderer: Singleton[WeasyPrintInvoiceDocumentRendererAdapter] = (
        Singleton(WeasyPrintInvoiceDocumentRendererAdapter)
    )
