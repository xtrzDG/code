"""
The reply budget (`uv run pytest -m perf tests/perf/test_reply_budget.py`):
WhatsApp customers write through Meta's signed webhook to an API process
and a worker process answers them with a model that takes 2 s. A finished
question is answered without the grouping penalty: the API's commit wakes
the worker (NOTIFY) and the reply leaves within 3 s of the claim, within
6 s of the webhook. A fragment ("Привет") waits MESSAGE_COALESCE_SECONDS
for the rest of the thought; the worker's due-time timer takes it then,
not at the lanes' next poll a minute later. Every inbox event records how
long it waited for the worker (`queue_to_claim_ms`).

The first question is the fresh worker's first turn: the reply guard's
locale data and the model SDK's Responses resource were loaded when the
worker started (`warm_turn_caches`, `openai_responses_client`), so it
keeps the same budget as the turns after it.

The world is tests/chaos's (reply_budget_world.py); skipped without
Postgres binaries.
"""

from collections.abc import Generator
from pathlib import Path

import pytest

from tests.chaos.chaos_world import ChaosWorld, chaos_world
from tests.chaos.fake_providers import ProviderState, fake_providers
from tests.chaos.llm_world import run_on_openai
from tests.chaos.meta_world import seed_whatsapp_restaurant
from tests.perf.reply_budget_world import (
    COALESCE_SECONDS,
    MILLISECONDS_PER_SECOND,
    MODEL_SECONDS,
    REPLY_BUDGET_ENVIRONMENT,
    ReplyTiming,
    time_reply,
)
from tests.storage.postgres_server import ThrowawayPostgresServer

pytestmark = pytest.mark.perf

CLAIM_TO_SEND_BUDGET_SECONDS: float = 3.0
WEBHOOK_TO_SEND_BUDGET_SECONDS: float = 6.0
# A job due now is taken at the API's commit, not at a poll.
TAKEN_AT_ONCE_MS: int = 1_000
# A job due later is taken when it is due (the timer's margin and a claim).
TAKEN_WHEN_DUE_MS: int = 1_000
QUESTIONS: tuple[str, ...] = (
    "Добрый вечер! Есть столик на двоих в 20:00?",
    "Hello! Do you have a table for four tonight?",
    "გამარჯობა! შაბათს ღია ხართ?",
)
FRAGMENT: str = "Привет"


@pytest.fixture
def budget_world(
    postgres_server: ThrowawayPostgresServer,
    migrated_template_database: str,
    tmp_path: Path,
) -> Generator[tuple[ChaosWorld, ProviderState, str]]:
    with (
        fake_providers() as (provider_url, providers),
        chaos_world(
            postgres_server,
            migrated_template_database,
            tmp_path,
            seed_whatsapp_restaurant,
            provider_url=provider_url,
        ) as world,
    ):
        providers.llm_delay_seconds = MODEL_SECONDS
        run_on_openai(world)
        world.environment.update(REPLY_BUDGET_ENVIRONMENT)
        api = world.start_api()
        world.start_worker()
        yield world, providers, api


def assert_within_budget(timing: ReplyTiming) -> None:
    # The model's 2 s are inside the measured span: it is the real path.
    assert timing.claim_to_send_seconds >= MODEL_SECONDS, timing
    assert timing.claim_to_send_seconds < CLAIM_TO_SEND_BUDGET_SECONDS, timing
    assert timing.webhook_to_send_seconds < WEBHOOK_TO_SEND_BUDGET_SECONDS, timing


def test_a_finished_question_is_answered_without_waiting_for_more(
    budget_world: tuple[ChaosWorld, ProviderState, str],
) -> None:
    world, providers, api = budget_world

    timings = [
        time_reply(world, providers, api, index, question)
        for index, question in enumerate(QUESTIONS)
    ]

    for timing in timings:
        assert timing.queue_to_claim_ms < TAKEN_AT_ONCE_MS, timing
        assert_within_budget(timing)


def test_a_fragment_waits_for_the_rest_and_is_taken_when_due(
    budget_world: tuple[ChaosWorld, ProviderState, str],
) -> None:
    world, providers, api = budget_world

    timing = time_reply(world, providers, api, 0, FRAGMENT)

    waited_ms: int = int(COALESCE_SECONDS * MILLISECONDS_PER_SECOND)
    assert waited_ms <= timing.queue_to_claim_ms < waited_ms + TAKEN_WHEN_DUE_MS
    assert_within_budget(timing)
