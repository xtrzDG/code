from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.postgres.document_collection_factory import (
    build_postgres_connection_pool,
)
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.email.smtp_email_client import SmtpEmailClient
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.meta.whatsapp_authentication_client import (
    WhatsAppAuthenticationClient,
)
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.telegram.telegram_bot_client import TelegramBotClient
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
from app.contracts.channel_clients import ElevenLabsApiClientContract


class ClientsContainer(containers.DeclarativeContainer):
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]

    # One pool for every Postgres collection; None without DATABASE_URL.
    postgres_pool: Singleton[PostgresConnectionPoolClient | None] = Singleton(
        build_postgres_connection_pool,
        settings=config.app_settings,
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
    elevenlabs_client: Singleton[ElevenLabsApiClientContract] = Singleton(
        build_elevenlabs_client,
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
