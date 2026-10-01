from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.adapters.storage.postgres.document_collection_factory import (
    build_postgres_connection_pool,
)
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.containers.config import ConfigContainer
from app.containers.factories import (
    build_elevenlabs_client,
    build_flitt_client,
    build_google_calendar_client,
    build_langfuse_ingestion_client,
)
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
