"""
A brownout at Meta holds up nothing else: with Meta's sends hanging for
10 s, a Telegram reply and a platform alert still go out within 2 s; after
five failures Meta's circuit opens (messages wait without a network call)
and lets one trial through 30 s later; and once Meta recovers every message
is delivered exactly once.
"""

import time
from collections import Counter

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.constants.resilience import CircuitState
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.storage import release_gates
from app.utilities.storage.release_gates import OPS_LANE_GATE
from tests.channels.channels_settings import TELEGRAM_BOT_TOKEN
from tests.channels.customer_outbox import queue_customer_message
from tests.channels.meta_payloads import PHONE_NUMBER_ID
from tests.channels.outbox_reads import outbox_of
from tests.platform.lane_fakes import running_worker
from tests.resilience.provider_fakes import MetaMode
from tests.resilience.send_bulkheads_world import META, SendBulkheadsWorld

# What the spec promises the other providers while Meta hangs.
OTHERS_WITHIN_SECONDS: float = 2.0
CUSTOMERS: int = 6


@pytest.fixture(params=[True, False], ids=["ops lane", "before the ops lane"])
def ops_lane_gate(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> bool:
    """
    The alerts' own lane once its release gate is open; before that (the
    release that ships it) they share the outbound lane, where Meta holds
    at most half of the threads.
    """

    is_open: bool = request.param
    monkeypatch.setattr(
        release_gates,
        "RELEASE_GATES",
        tuple(
            gate.model_copy(update={"is_open": is_open})
            if gate.name == OPS_LANE_GATE
            else gate
            for gate in release_gates.RELEASE_GATES
        ),
    )
    return is_open


def channels(world: SendBulkheadsWorld) -> tuple[ChannelDocument, ChannelDocument]:
    business = world.add_business(world.add_user("owner"))
    whatsapp = world.add_channel(business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
    telegram = world.add_channel(
        business.id, ChannelKind.TELEGRAM, "funicular_vr_bot", TELEGRAM_BOT_TOKEN
    )
    return whatsapp, telegram


def whatsapp_replies(
    world: SendBulkheadsWorld, whatsapp: ChannelDocument
) -> list[OutboundMessageDocument]:
    return [
        queue_customer_message(
            world,
            whatsapp,
            f"99559900000{number}",
            OutboundMessageKind.CUSTOMER_REPLY,
            text=f"Reply {number}.",
        )
        for number in range(CUSTOMERS)
    ]


def drain(world: SendBulkheadsWorld) -> None:
    """Run every job that comes due, the clock moving a minute at a time."""

    worker = world.guarded_worker()
    for _ in range(10):
        world.clock.advance(60)
        world.ticks.advance(60)
        worker.run_queued_jobs()


def assert_each_delivered_once(
    world: SendBulkheadsWorld, business_id: BusinessId, expected: int
) -> None:
    outbox = outbox_of(world, business_id)
    assert len(outbox) == expected
    assert {message.status for message in outbox} == {OutboundMessageStatus.DELIVERED}
    accepted = Counter(world.meta.accepted)
    assert sorted(accepted) == sorted(
        str(message.customer.channel_user_id)
        for message in outbox
        if message.customer is not None
        and message.customer.channel is ChannelKind.WHATSAPP
    )
    assert set(accepted.values()) == {1}


def test_a_hanging_meta_holds_up_neither_telegram_nor_the_alerts(
    ops_lane_gate: bool,
) -> None:
    world = SendBulkheadsWorld(MetaMode.HANG)
    whatsapp, telegram = channels(world)
    whatsapp_replies(world, whatsapp)

    with running_worker(world.guarded_worker(), world.meta.answer_from_now_on):
        assert world.meta.wait_for_hanging(2)
        started: float = time.monotonic()
        queue_customer_message(
            world, telegram, "100200300", OutboundMessageKind.CUSTOMER_REPLY
        )
        world.queue_platform_alert("The inbound queue is 12 minutes behind.")

        assert world.telegram.wait_for_sends(2, OTHERS_WITHIN_SECONDS)
        elapsed: float = time.monotonic() - started

    assert elapsed < OTHERS_WITHIN_SECONDS
    assert world.telegram.sent_with.count(TELEGRAM_BOT_TOKEN) == 1
    assert world.platform_bot_sends() == 1
    # Meta never held more than its half of the outbound threads.
    assert len(world.meta.hung) == 2
    assert world.meta.most_in_flight == 2

    drain(world)

    assert_each_delivered_once(world, whatsapp.business_id, CUSTOMERS + 1)
    assert world.telegram.sent_with.count(TELEGRAM_BOT_TOKEN) == 1
    # The two that hung spent an attempt each; the ones that found Meta
    # busy waited without spending one.
    attempts = sorted(
        int(message.attempts) for message in outbox_of(world, whatsapp.business_id)
    )
    assert attempts == [1] * (CUSTOMERS - 1) + [2] * 2


def test_five_timeouts_open_meta_and_it_tries_again_after_thirty_seconds() -> None:
    world = SendBulkheadsWorld(MetaMode.FAIL)
    whatsapp, _ = channels(world)
    queued = whatsapp_replies(world, whatsapp)
    worker = world.guarded_worker()

    worker.run_queued_jobs()

    # Five sends timed out; the sixth found the circuit open and made no call.
    assert len(world.meta.attempts) == 5
    assert world.circuit_breaker.state(META) is CircuitState.OPEN
    last = world.outbound_message_repo.get(whatsapp.business_id, queued[-1].id)
    assert last is not None and last.status is OutboundMessageStatus.PENDING
    assert last.last_failure_reason is DeliveryFailureReason.PROVIDER_UNAVAILABLE
    assert last.next_attempt_at is not None
    assert int(last.next_attempt_at) - int(world.clock.now_microseconds()) == (
        30 * 1_000_000
    )

    # 29 s later the circuit still refuses: the due messages wait, no call.
    world.ticks.advance(29)
    world.clock.advance(29)
    worker.run_queued_jobs()
    assert len(world.meta.attempts) == 5
    assert world.circuit_breaker.state(META) is CircuitState.OPEN

    # At 30 s the circuit lets one trial through: Meta answers and the
    # circuit closes, so the rest follow.
    world.meta.answer_from_now_on()
    world.ticks.advance(1)
    assert world.circuit_breaker.seconds_until_trial(META) is None
    drain(world)

    assert world.circuit_states.of(META) == [
        CircuitState.CLOSED,
        CircuitState.OPEN,
        CircuitState.HALF_OPEN,
        CircuitState.CLOSED,
    ]
    assert len(world.meta.attempts) == 5 + CUSTOMERS
    assert_each_delivered_once(world, whatsapp.business_id, CUSTOMERS)
