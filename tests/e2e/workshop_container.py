"""The real AppContainer with every edge replaced by the workshop's fakes."""

from collections.abc import Mapping
from typing import Protocol, cast

from dependency_injector import providers

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.clients.anthropic.anthropic_messages_client import AnthropicMessagesClient
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.langfuse.langfuse_ingestion_client import LangfuseIngestionClient
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.containers.app import AppContainer
from app.schemas.dto.live_events import LiveStreamLimits
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.live_events.constrained_floats import (
    LiveStreamHeartbeatSeconds,
    LiveStreamLifetimeSeconds,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.billing.rate_feed_fakes import fixture_rate_clients
from tests.e2e.edge_fakes import (
    CapturingOtpDelivery,
    MovableClock,
    RecordedHttp,
    answer_elevenlabs,
    answer_telegram,
    answer_with_empty_object,
    build_transport,
    refuse_anthropic_sdk,
    refuse_openai_sdk,
)
from tests.e2e.harness_settings import ELEVENLABS_BASE_URL


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


# A test client reads a response to its end: live streams here end after a
# moment (after what was published while they were open).
E2E_LIVE_STREAM_LIMITS: LiveStreamLimits = LiveStreamLimits(
    heartbeat_seconds=LiveStreamHeartbeatSeconds(0.05),
    lifetime_seconds=LiveStreamLifetimeSeconds(0.1),
)


def replace_provider[Provided](
    provider: providers.Provider[Provided],
    value: Provided,
) -> None:
    """Make a container provider return a ready object (the test's edge)."""

    cast(OverridableProvider, provider).override(providers.Object(value))


def build_workshop_container(
    environment: Mapping[str, str],
    clock: MovableClock,
    otp: CapturingOtpDelivery,
    llm: ScriptedLlmAdapter,
    telegram: RecordedHttp,
    meta: RecordedHttp,
    elevenlabs: RecordedHttp,
    google: RecordedHttp,
    langfuse: RecordedHttp,
) -> AppContainer:
    """The real container with every edge replaced (nothing leaves the test)."""

    settings = assemble_app_settings(environment)
    container = AppContainer()
    replace_provider(container.config.app_settings, settings)
    replace_provider(container.time_provider.microsecond_wall_clock, clock.wall_clock)
    replace_provider(container.adapters.routing_llm_adapter, llm)
    replace_provider(container.facilitators.otp_delivery_facilitator, otp)
    replace_provider(container.facilitators.live_stream_limits, E2E_LIVE_STREAM_LIMITS)
    replace_provider(
        container.clients.openai_responses_client,
        OpenAiResponsesClient(
            base_url=settings.openai_base_url,
            project_id=None,
            sdk_factory=refuse_openai_sdk,
        ),
    )
    replace_provider(
        container.clients.anthropic_messages_client,
        AnthropicMessagesClient(sdk_factory=refuse_anthropic_sdk),
    )
    replace_provider(
        container.clients.telegram_bot_client,
        TelegramBotClient(transport=build_transport(telegram, answer_telegram)),
    )
    replace_provider(
        container.clients.meta_graph_client,
        MetaGraphClient(transport=build_transport(meta, answer_with_empty_object)),
    )
    replace_provider(
        container.clients.elevenlabs_client,
        ElevenLabsClient(
            api_key=PlatformSecret("xi-e2e-key"),
            base_url=PublicBaseUrl(ELEVENLABS_BASE_URL),
            transport=build_transport(elevenlabs, answer_elevenlabs),
        ),
    )
    # The central banks' rate feeds read fixture files (dated 2026-10-02/03).
    nbg_rates_client, ecb_rates_client = fixture_rate_clients()
    replace_provider(container.clients.nbg_rates_client, nbg_rates_client)
    replace_provider(container.clients.ecb_rates_client, ecb_rates_client)
    replace_provider(
        container.clients.google_calendar_client,
        GoogleCalendarClient(
            client_id=None,
            client_secret=None,
            redirect_url=None,
            transport=build_transport(google, answer_with_empty_object),
        ),
    )
    if (
        settings.langfuse_public_key is not None
        and settings.langfuse_secret_key is not None
    ):
        replace_provider(
            container.clients.langfuse_ingestion_client,
            LangfuseIngestionClient(
                host=settings.langfuse_host,
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                transport=build_transport(langfuse, answer_with_empty_object),
            ),
        )

    return container
