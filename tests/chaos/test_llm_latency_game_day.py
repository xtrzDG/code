"""
Game day: the language model provider answers after 30 seconds. With
LLM_CALL_TIMEOUT_SECONDS at 2 every model call gives up (once retried),
so none of twenty website visitors gets the assistant's answer: each is
told a colleague will answer (the turn's handoff) instead of silence. The
next check of the platform alerts pages LLM_ERRORS and /status shows the
chat channels down; once the provider is fast again new visitors are
answered at once, the circuit closes and the alert resolves.

docs/operations/runbooks/llm-outage.md is the runbook this rehearses (the
single-provider case: LLM_FALLBACK_MODEL_ID=off).
"""

from collections.abc import Generator
from functools import partial
from pathlib import Path

import pytest

from tests.chaos.chaos_world import (
    MINUTE,
    ChaosWorld,
    chaos_world,
    component_levels,
    wait_for,
)
from tests.chaos.fake_providers import REPLY_TEXT, ProviderState, fake_providers
from tests.chaos.llm_world import (
    OPENAI_ONLY,
    assistant_answers,
    run_on_openai,
    visitor_writes,
)
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.two_process_world import seed_restaurant

VISITORS: int = 20
LLM_TITLE: str = "Model calls fail"
SLOW_PROVIDER_SECONDS: float = 30.0
QUESTION: str = "Добрый вечер! Есть столик на двоих в 20:00?"
# Seconds between two looks at a visitor's chat (the widget's own pace).
WIDGET_POLL: float = 3.0


@pytest.fixture
def llm_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path: Path,
) -> Generator[tuple[ChaosWorld, ProviderState]]:
    with (
        fake_providers() as (provider_url, providers),
        chaos_world(
            postgres_server,
            migrated_template_database,
            tmp_path,
            seed_restaurant,
            provider_url=provider_url,
        ) as world,
    ):
        run_on_openai(world)
        world.environment.update(OPENAI_ONLY)
        yield world, providers


def is_answered(world: ChaosWorld, api_url: str, index: int) -> bool:
    return bool(assistant_answers(world, api_url, index))


def is_answered_by_the_model(world: ChaosWorld, api_url: str, index: int) -> bool:
    return any(REPLY_TEXT in text for text in assistant_answers(world, api_url, index))


def test_a_slow_model_pages_takes_the_chat_down_and_recovers(
    llm_world: tuple[ChaosWorld, ProviderState],
) -> None:
    world, providers = llm_world
    providers.llm_delay_seconds = SLOW_PROVIDER_SECONDS
    api = world.start_api()
    world.start_worker()

    for index in range(VISITORS):
        visitor_writes(world, api, index, QUESTION)
    # Every visitor's turn tried the model (and its retry) and gave up ...
    wait_for(lambda: providers.llm_calls >= 2 * VISITORS, 180, "the failed model calls")
    # ... and the visitor heard that a colleague answers instead.
    wait_for(partial(is_answered, world, api, 0), 60, "the handoff notice", WIDGET_POLL)
    assert not is_answered_by_the_model(world, api, 0)

    # The next five-minute check of the platform alerts sees the failures.
    world.clock.advance(5 * MINUTE)
    wait_for(lambda: bool(world.alerts(LLM_TITLE)), 60, "the LLM_ERRORS alert")
    [firing] = world.alerts(LLM_TITLE)
    assert firing.headline == f"[SEV1] FIRING: {LLM_TITLE}"
    levels = component_levels(api)
    assert {levels["chat"], levels["meta"], levels["telegram"]} == {"outage"}
    assert levels["cabinet"] == "operational"

    # The provider is fast again: a new visitor gets the model's answer ...
    providers.llm_delay_seconds = 0.0
    visitor_writes(world, api, VISITORS, QUESTION)
    wait_for(
        partial(is_answered_by_the_model, world, api, VISITORS),
        60,
        "the model's answer",
        WIDGET_POLL,
    )
    # ... and once the failures leave the alert's window, all clear.
    world.clock.advance(31 * MINUTE)
    wait_for(lambda: len(world.alerts(LLM_TITLE)) == 2, 60, "the recovery")
    assert world.alerts(LLM_TITLE)[1].headline == f"[SEV1] RESOLVED: {LLM_TITLE}"
    assert component_levels(api)["chat"] == "operational"
