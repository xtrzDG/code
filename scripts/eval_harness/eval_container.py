"""
The real AppContainer for an evaluation run: storage in memory, a clock
that starts every scenario on Monday 2026-10-05 at 12:00 in Tbilisi and
moves one millisecond per reading (so stored rows keep their order), and
one language-model seam the harness points at the adapter of the scenario
sample being played (replay, recording, scripted or a live provider), and
the customers' photos kept in memory.
"""

import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Protocol, cast

from dependency_injector import providers
from typed_time_provider import Microseconds, WallClock

from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.containers.app import AppContainer
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import LlmProvider
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.conversations.llm_models import resolve_llm_provider
from scripts.eval_harness.media_inputs import InMemoryMediaStorage

SCENARIO_START: datetime = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
NANOSECONDS_PER_SECOND: int = 1_000_000_000
TICK_NANOSECONDS: int = 1_000_000
# Provider settings a live run takes from the environment (GitHub secrets).
PROVIDER_VARIABLES: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_PROJECT_ID",
    "ANTHROPIC_API_KEY",
)
BASE_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "test",
    "APP_BASE_URL": "https://api.evals.example",
    # A technical key for the in-memory run; nothing it encrypts is kept.
    "ENCRYPTION_KEY": "evals-encryption-secret-0000000000000000",  # gitleaks:allow
    "LLM_CHAT_EFFORT": "low",
}


class OverridableProvider(Protocol):
    def override(self, provider: object) -> object: ...


class SteppingClock:
    """Nanoseconds since the epoch: a fixed start, one tick per reading."""

    def __init__(self, start: datetime = SCENARIO_START) -> None:
        self._start: int = int(start.timestamp()) * NANOSECONDS_PER_SECOND
        self._now: int = self._start

    def __call__(self) -> int:
        self._now += TICK_NANOSECONDS
        return self._now

    def reset(self) -> None:
        """Back to the start: every scenario sample sees the same moments."""

        self._now = self._start


class SwitchableLlmAdapter(LlmAdapterContract):
    """The container's model seam; `use` points it at a scenario's adapter."""

    def __init__(self) -> None:
        self._current: LlmAdapterContract | None = None

    def use(self, adapter: LlmAdapterContract) -> None:
        self._current = adapter

    def _adapter(self) -> LlmAdapterContract:
        if self._current is None:
            raise RuntimeError("No language model is selected for this scenario.")

        return self._current

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._adapter().build_user_text_turn(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return self._adapter().build_user_media_turn(text, images)

    def build_tool_results_turn(
        self, results: list[LlmToolResult]
    ) -> LlmProviderPayload:
        return self._adapter().build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        return self._adapter().complete(request)


def build_environment(
    assistant_model: LlmModelId,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Settings of the run: the assistant model and any provider keys."""

    source: Mapping[str, str] = os.environ if environ is None else environ
    provider: LlmProvider = (
        resolve_llm_provider(assistant_model) or LlmProvider.SCRIPTED
    )
    environment: dict[str, str] = {
        **BASE_ENVIRONMENT,
        "LLM_PROVIDER": provider.value,
        "LLM_MODEL_ID": str(assistant_model),
    }
    for name in PROVIDER_VARIABLES:
        value: str | None = source.get(name)
        if value:
            environment[name] = value

    return environment


def build_eval_container(
    environment: Mapping[str, str],
    clock: SteppingClock,
    seam: SwitchableLlmAdapter,
) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    replace_provider(
        container.time_provider.microsecond_wall_clock,
        WallClock(preferred_time_unit_type=Microseconds, unix_nanosecond_factory=clock),
    )
    replace_provider(container.adapters.routing_llm_adapter, seam)
    # Photos a scenario sends stay in memory, never in a directory.
    replace_provider(container.adapters.media.media_storage, InMemoryMediaStorage())
    return container


def build_provider_router(
    container: AppContainer, scripted_adapter: LlmAdapterContract
) -> RoutingLlmAdapter:
    """The live providers of the container plus the dataset's scripted model."""

    return RoutingLlmAdapter(
        openai_adapter=container.adapters.openai_llm_adapter(),
        anthropic_adapter=container.adapters.anthropic_llm_adapter(),
        scripted_adapter=scripted_adapter,
    )


def replace_provider(provider: object, value: object) -> None:
    cast(OverridableProvider, provider).override(providers.Object(value))
