from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.postgres.document_collection_factory import (
    build_postgres_connection_pool,
)
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.ecb.ecb_rates_client import EcbRatesClient
from app.clients.email.smtp_email_client import SmtpEmailClient
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.http.safe_http_fetcher import SafeHttpFetcher
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.meta.meta_media_client import MetaMediaClient
from app.clients.meta.meta_token_debug_client import MetaTokenDebugClient
from app.clients.meta.meta_typing_client import MetaTypingClient
from app.clients.meta.whatsapp_authentication_client import (
    WhatsAppAuthenticationClient,
)
from app.clients.nbg.nbg_rates_client import NbgRatesClient
from app.clients.object_storage.object_storage_client_factory import (
    build_object_storage_client,
)
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.openai.openai_transcription_client import (
    OpenAiTranscriptionClient,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.clients.telegram.telegram_file_client import TelegramFileClient
from app.clients.telegram.telegram_gateway_client import TelegramGatewayClient
from app.clients.turnstile.turnstile_verification_client import (
    TurnstileVerificationClient,
)
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.clients.webpush.web_push_client import WebPushClient
from app.containers.config import ConfigContainer
from app.containers.factories import (
    build_elevenlabs_client,
    build_flitt_client,
    build_google_calendar_client,
    build_langfuse_ingestion_client,
    build_smtp_email_client,
    build_telegram_gateway_client,
    build_turnstile_verification_client,
    build_twilio_messaging_client,
    build_whatsapp_authentication_client,
)
from app.containers.notification_factories import build_web_push_client
from app.containers.telemetry_factories import build_pool_instruments
from app.containers.utilities import UtilitiesContainer
from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.object_storage import ObjectStorageClientContract
from app.contracts.web_fetching import SafeHttpFetcherContract


class ClientsContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # One pool for every Postgres collection; None without DATABASE_URL. It
    # reports waits and connections in use, and traces its statements.
    postgres_pool: Singleton[PostgresConnectionPoolClient | None] = Singleton(
        build_postgres_connection_pool,
        settings=config.app_settings,
        instruments=Singleton(
            build_pool_instruments,
            metrics=utilities.service_metrics,
            span_tracer=utilities.span_tracer,
        ),
    )
    # SDK clients are created on first use, so no API key is needed to start.
    openai_responses_client: Singleton[OpenAiResponsesClient] = Singleton(
        OpenAiResponsesClient,
        base_url=config.app_settings.provided.openai_base_url,
        project_id=config.app_settings.provided.openai_project_id,
    )
    anthropic_messages_client: Singleton[AnthropicMessagesClient] = Singleton(
        AnthropicMessagesClient
    )
    # One Telegram client serves every business bot (token per call).
    telegram_bot_client: Singleton[TelegramBotClient] = Singleton(TelegramBotClient)
    meta_graph_client: Singleton[MetaGraphClient] = Singleton(MetaGraphClient)
    meta_typing_client: Singleton[MetaTypingClient] = Singleton(MetaTypingClient)
    # Meta channel tokens' expiry, asked with the platform's app.
    meta_token_debug_client: Singleton[MetaTokenDebugClient] = Singleton(
        MetaTokenDebugClient
    )
    # Files customers send: platform downloads, speech-to-text (EU project).
    meta_media_client: Singleton[MetaMediaClient] = Singleton(MetaMediaClient)
    telegram_file_client: Singleton[TelegramFileClient] = Singleton(TelegramFileClient)
    openai_transcription_client: Singleton[OpenAiTranscriptionClient] = Singleton(
        OpenAiTranscriptionClient,
        base_url=config.app_settings.provided.openai_base_url,
        project_id=config.app_settings.provided.openai_project_id,
    )
    elevenlabs_client: Singleton[ElevenLabsApiClientContract] = Singleton(
        build_elevenlabs_client,
        settings=config.app_settings,
    )
    # The EU bucket of call recordings (RECORDINGS_STORAGE=s3), else None.
    object_storage_client: Singleton[ObjectStorageClientContract | None] = Singleton(
        build_object_storage_client,
        settings=config.app_settings,
    )
    google_calendar_client: Singleton[GoogleCalendarClient] = Singleton(
        build_google_calendar_client,
        settings=config.app_settings,
    )
    flitt_client: Singleton[FlittClient | None] = Singleton(
        build_flitt_client,
        settings=config.app_settings,
    )
    langfuse_ingestion_client: Singleton[LangfuseIngestionClient | None] = Singleton(
        build_langfuse_ingestion_client,
        settings=config.app_settings,
    )
    # Login code providers; each is None until its settings are present.
    twilio_messaging_client: Singleton[TwilioMessagingClient | None] = Singleton(
        build_twilio_messaging_client,
        settings=config.app_settings,
    )
    telegram_gateway_client: Singleton[TelegramGatewayClient | None] = Singleton(
        build_telegram_gateway_client,
        settings=config.app_settings,
    )
    whatsapp_authentication_client: Singleton[WhatsAppAuthenticationClient | None] = (
        Singleton(
            build_whatsapp_authentication_client,
            settings=config.app_settings,
        )
    )
    smtp_email_client: Singleton[SmtpEmailClient | None] = Singleton(
        build_smtp_email_client,
        settings=config.app_settings,
    )
    # The bot check of risky login code requests; None until both
    # TURNSTILE_* keys are set.
    turnstile_verification_client: Singleton[TurnstileVerificationClient | None] = (
        Singleton(
            build_turnstile_verification_client,
            settings=config.app_settings,
        )
    )
    # Notifications on cabinet users' devices; None until WEB_PUSH_VAPID_*
    # are set.
    web_push_client: Singleton[WebPushClient | None] = Singleton(
        build_web_push_client,
        settings=config.app_settings,
    )
    # Outside web addresses (a business's website, menu links): public
    # addresses only, connected at the vetted address (the SSRF guard).
    safe_http_fetcher: Singleton[SafeHttpFetcherContract] = Singleton(SafeHttpFetcher)
    # The central banks' daily exchange rates, read through the same guard:
    # the National Bank of Georgia (lari) and the ECB (euro reference rates).
    nbg_rates_client: Singleton[NbgRatesClient] = Singleton(
        NbgRatesClient, safe_http_fetcher=safe_http_fetcher
    )
    ecb_rates_client: Singleton[EcbRatesClient] = Singleton(
        EcbRatesClient, safe_http_fetcher=safe_http_fetcher
    )
