"""
The reply budget's world (tests/perf/test_reply_budget.py): the game days'
two-process harness (tests/chaos) with the restaurant's WhatsApp number,
a model that answers after 2 s (the fake OpenAI provider, the scripted
model of the budget) and lanes that poll once a minute, so a claim within
seconds was a wake-up: NOTIFY at commit for a job due now, the worker's
due-time timer for a job due later.

What the customer saw is read from the fake Meta Graph API (when the
reply was posted to them), what the worker saw from the customer's inbox
event (when it was stored, and `queue_to_claim_ms`, how long it waited
for the worker to take it).
"""

import time
from dataclasses import dataclass
from functools import partial

from tests.chaos.chaos_world import ChaosWorld, wait_for
from tests.chaos.fake_providers import ProviderState
from tests.chaos.llm_world import OPENAI_ONLY
from tests.chaos.meta_world import customer_writes

MODEL_SECONDS: float = 2.0
COALESCE_SECONDS: int = 3
# The lanes' polls are a minute apart: only a wake-up claims within seconds.
POLL_SECONDS: int = 60
REPLY_WAIT_SECONDS: float = 30.0
MICROSECONDS_PER_SECOND: float = 1_000_000.0
MILLISECONDS_PER_SECOND: float = 1_000.0

REPLY_BUDGET_ENVIRONMENT: dict[str, str] = {
    **OPENAI_ONLY,
    # The 2 s model answers well within one call's timeout.
    "LLM_CALL_TIMEOUT_SECONDS": "10",
    "MESSAGE_COALESCE_SECONDS": str(COALESCE_SECONDS),
    "WORKER_POLL_SECONDS": str(POLL_SECONDS),
    "WORKER_INBOUND_POLL_SECONDS": str(POLL_SECONDS),
}


@dataclass(frozen=True)
class ReplyTiming:
    """One customer message and its reply, as both sides saw them."""

    webhook_to_send_seconds: float
    claim_to_send_seconds: float
    queue_to_claim_ms: int


def customer_number(index: int) -> str:
    """The WhatsApp number `customer_writes` writes from for `index`."""

    return f"9955550{index:05d}"


def reply_posted_at(
    providers: ProviderState, sender: str, after: float
) -> float | None:
    """When the first text message to `sender` reached Meta after `after`."""

    for posted_at, body in list(providers.meta_posts):
        if (
            posted_at >= after
            and body.get("type") == "text"
            and body.get("to") == sender
        ):
            return posted_at

    return None


def inbound_claim(world: ChaosWorld, sender: str) -> tuple[float, int]:
    """When the sender's one inbox event was stored (s) and its wait (ms)."""

    rows = world.query(
        "select (document ->> 'created_at')::bigint, "
        "(document ->> 'queue_to_claim_ms')::bigint "
        "from workshop.inbound_events "
        "where document ->> 'channel' = 'whatsapp' "
        "and document -> 'customer_message' ->> 'channel_user_id' = %s",
        sender,
    )
    assert len(rows) == 1, rows
    [(created_at, waited)] = rows
    assert waited is not None, "the worker took the event without timing it"
    return int(created_at) / MICROSECONDS_PER_SECOND, int(waited)


def time_reply(
    world: ChaosWorld,
    providers: ProviderState,
    api_url: str,
    index: int,
    text: str,
) -> ReplyTiming:
    """Customer `index` writes `text` once; how long until they had a reply."""

    sender = customer_number(index)
    written = time.time()
    customer_writes(world, api_url, index, text)
    is_answered = partial(reply_posted_at, providers, sender, written)
    wait_for(
        lambda: is_answered() is not None,
        REPLY_WAIT_SECONDS,
        f"the reply to customer {index}",
        0.05,
    )
    sent = is_answered()
    assert sent is not None
    stored, waited = inbound_claim(world, sender)
    claimed = stored + waited / MILLISECONDS_PER_SECOND
    return ReplyTiming(
        webhook_to_send_seconds=sent - written,
        claim_to_send_seconds=sent - claimed,
        queue_to_claim_ms=waited,
    )
