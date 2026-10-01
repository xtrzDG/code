"""
Small builders the containers use where a provider depends on optional
settings (a missing key switches to a stand-in instead of failing startup).
"""

from pathlib import Path

from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.elevenlabs.unconfigured_elevenlabs_client import (
    UnconfiguredElevenLabsClient,
)
from app.clients.flitt.flitt_client import FlittClient
from app.clients.google.google_calendar_client import (
    GoogleCalendarClient,
    build_google_calendar_redirect_url,
)
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.observability import LlmTraceFacilitatorContract
from app.facilitators.observability.langfuse_trace_facilitator import (
    LangfuseTraceFacilitator,
)
from app.facilitators.observability.null_trace_facilitator import (
    NullTraceFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.utilities.conversations.llm_models import resolve_llm_provider

# Menu import reads photos and PDFs with an OpenAI vision model (brain slice);
# used when the chat model itself is not an OpenAI model.
DEFAULT_MENU_EXTRACTION_MODEL_ID: LlmModelId = LlmModelId("gpt-5-mini")


def build_elevenlabs_client(settings: AppSettings) -> ElevenLabsApiClientContract:
    """The ElevenLabs API client, or a stand-in that reports the missing key."""

    if settings.elevenlabs_api_key is None:
        return UnconfiguredElevenLabsClient()

    return ElevenLabsClient(
        api_key=settings.elevenlabs_api_key,
        base_url=settings.elevenlabs_api_base_url,
    )


def build_flitt_client(settings: AppSettings) -> FlittClient | None:
    """Flitt client when both merchant settings are present, else None."""

    if settings.flitt_merchant_id is None or settings.flitt_secret_key is None:
        return None

    return FlittClient(
        merchant_id=settings.flitt_merchant_id,
        secret_key=settings.flitt_secret_key,
    )


def build_google_calendar_client(settings: AppSettings) -> GoogleCalendarClient:
    """Google Calendar client; missing settings make its calls fail with 502."""

    return GoogleCalendarClient(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        redirect_url=build_google_calendar_redirect_url(settings.app_base_url),
    )


def build_langfuse_ingestion_client(
    settings: AppSettings,
) -> LangfuseIngestionClient | None:
    """Langfuse client when both keys are set, else None (no quality journal)."""

    if settings.langfuse_public_key is None or settings.langfuse_secret_key is None:
        return None

    return LangfuseIngestionClient(
        host=settings.langfuse_host,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
    )


def build_llm_trace_facilitator(
    langfuse_client: LangfuseIngestionClient | None,
) -> LlmTraceFacilitatorContract:
    """Langfuse journal when configured, otherwise traces are discarded."""

    if langfuse_client is None:
        return NullTraceFacilitator()

    return LangfuseTraceFacilitator(client=langfuse_client)


def select_menu_extraction_model_id(settings: AppSettings) -> LlmModelId:
    """The chat model when it is an OpenAI model, else the default vision model."""

    if resolve_llm_provider(settings.llm_model_id) is LlmProvider.OPENAI:
        return settings.llm_model_id

    return DEFAULT_MENU_EXTRACTION_MODEL_ID


def resolve_recordings_directory(settings: AppSettings) -> Path:
    """Directory of call recordings kept on this server."""

    return Path(str(settings.recordings_directory))
