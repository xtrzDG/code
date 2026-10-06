"""
One process of a game day's world:

    python -m tests.chaos.chaos_process api <port>
    python -m tests.chaos.chaos_process worker

The real application or worker on the test database (settings from the
environment, DATABASE_URL among them), with only the edges a game day
needs moved: the clock reads the shared offset (`chaos_clock.py`), the
staff providers write what they send to a file (`chaos_sends.py`), and,
with CHAOS_PROVIDER_URL, Meta's Graph API and OpenAI's Responses API are
the test's fake providers (`fake_providers.py`), which can black-hole a
request or answer after a pause. Everything else is production code.
"""

import os
import sys
from pathlib import Path
from typing import cast

import httpx
import openai
import uvicorn
from dependency_injector import providers

from app.clients.meta import meta_graph_client, meta_typing_client
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.meta.meta_media_client import MetaMediaClient
from app.clients.meta.meta_typing_client import MetaTypingClient
from app.clients.openai.openai_responses_client import OpenAiResponsesClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.containers.app import AppContainer
from app.main import build_application
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.utilities.observability.logging_setup import configure_logging
from app.worker_main import main as run_worker
from tests.chaos.chaos_clock import (
    CLOCK_FILE_VARIABLE,
    shifted_monotonic_clock,
    shifted_nanosecond_wall_clock,
    shifted_wall_clock,
)
from tests.chaos.chaos_sends import SENDS_FILE_VARIABLE, RecordingStaffSender
from tests.e2e.edge_fakes import answer_telegram
from tests.e2e.workshop_container import OverridableProvider, replace_provider

PROVIDER_URL_VARIABLE: str = "CHAOS_PROVIDER_URL"
OPENAI_DOCUMENTED_BASE_URL: str = "https://eu.api.openai.com/v1"
# A black-holed host never answers: each request gives up after this.
PROVIDER_TIMEOUT_SECONDS: float = 1.0


def move_the_clock(container: AppContainer, clock_file: Path) -> None:
    replace_provider(
        container.time_provider.microsecond_wall_clock, shifted_wall_clock(clock_file)
    )
    replace_provider(
        container.time_provider.wall_clock, shifted_nanosecond_wall_clock(clock_file)
    )
    replace_provider(
        container.time_provider.monotonic_clock, shifted_monotonic_clock(clock_file)
    )


def use_fake_providers(container: AppContainer, provider_url: str) -> None:
    """Meta and OpenAI behind the test's server; requests give up in 1 s."""

    meta_graph_client.REQUEST_TIMEOUT_SECONDS = PROVIDER_TIMEOUT_SECONDS
    meta_typing_client.TYPING_TIMEOUT_SECONDS = PROVIDER_TIMEOUT_SECONDS
    meta_url = f"{provider_url}/meta"
    replace_provider(
        container.clients.meta_graph_client, MetaGraphClient(base_url=meta_url)
    )
    replace_provider(
        container.clients.meta_typing_client, MetaTypingClient(base_url=meta_url)
    )
    replace_provider(
        container.clients.meta_media_client, MetaMediaClient(base_url=meta_url)
    )

    def build_sdk() -> openai.OpenAI:
        return openai.OpenAI(
            api_key="sk-chaos-0000",
            base_url=f"{provider_url}/openai/v1",
            max_retries=0,
        )

    replace_provider(
        container.clients.openai_responses_client,
        OpenAiResponsesClient(
            base_url=PublicBaseUrl(OPENAI_DOCUMENTED_BASE_URL),
            project_id=None,
            sdk_factory=build_sdk,
        ),
    )


def answer_telegram_locally(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=answer_telegram(request))


def build_container() -> AppContainer:
    container = AppContainer()
    move_the_clock(container, Path(os.environ[CLOCK_FILE_VARIABLE]))
    # The platform bot is configured (staff notifications go out) but its
    # webhook registration at startup stays here.
    replace_provider(
        container.clients.telegram_bot_client,
        TelegramBotClient(transport=httpx.MockTransport(answer_telegram_locally)),
    )
    # The concrete provider takes the recorder that keeps its contract.
    cast(
        OverridableProvider, container.facilitators.staff_notification_sender
    ).override(
        providers.Object(RecordingStaffSender(Path(os.environ[SENDS_FILE_VARIABLE])))
    )
    provider_url: str | None = os.environ.get(PROVIDER_URL_VARIABLE)
    if provider_url:
        use_fake_providers(container, provider_url)
    return container


def main() -> None:
    role: str = sys.argv[1]
    container = build_container()
    if role == "api":
        uvicorn.run(
            build_application(container),
            host="127.0.0.1",
            port=int(sys.argv[2]),
            log_level="warning",
        )
        return

    configure_logging(container.config.app_settings().log_format)
    raise SystemExit(run_worker(container))


if __name__ == "__main__":
    main()
