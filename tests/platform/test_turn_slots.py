"""
Turn places: a customer turn takes one before the customer's lock (which
holds a database connection for the whole turn), so turns waiting for the
model hold nothing; the owners' test chat has places of its own and asks
the owner to try again (429) instead of taking every request thread.
"""

import threading
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager

import pytest

from app.pipelines.conversations.customer_message_pipeline import (
    CustomerMessagePipeline,
)
from app.registries.turns.turn_slot_registry import (
    TEST_CHAT_SLOT_WAIT,
    TurnSlotRegistry,
    build_customer_turn_slots,
    build_test_chat_slots,
    refuse_busy_test_chat,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.conversations import AssistantReply, InboundMessage
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    RateLimitedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_integers import (
    RetryAfterSeconds,
    TurnSlotCount,
    TurnSlotWaitSeconds,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.platform.lane_fakes import wait_until

BUSINESS_ID: BusinessId = BusinessId("business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10")


def message(visitor: str) -> InboundMessage:
    return InboundMessage(
        business_id=BUSINESS_ID,
        channel=ChannelKind.WEB_CHAT,
        channel_user_id=ChannelUserId(visitor),
        text=MessageText("A table for two?"),
    )


class RecordingLocks:
    """The customer locks: who holds one now, and who ever took one."""

    def __init__(self) -> None:
        self.taken: list[str] = []

    def lock_for_customer(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> AbstractContextManager[object]:
        del business_id, channel
        return self._held(str(channel_user_id))

    @contextmanager
    def _held(self, visitor: str) -> Generator[object]:
        self.taken.append(visitor)
        yield visitor


class GatedTurns:
    """A turn waits for the test to let it finish (a slow model)."""

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.started: list[str] = []

    def execute(self, input_data: InboundMessage) -> AssistantReply:
        self.started.append(str(input_data.channel_user_id))
        self.gate.wait(timeout=10)
        return AssistantReply(
            conversation_id=ConversationId(),
            text=MessageText("Yes."),
            language=LanguageTag("en"),
            is_handed_off=False,
        )


def test_a_turn_waiting_for_a_place_holds_no_customer_lock() -> None:
    locks = RecordingLocks()
    turns = GatedTurns()
    pipeline = CustomerMessagePipeline(
        turn_orchestrator=turns,
        customer_locks=locks,
        turn_slots=TurnSlotRegistry(
            TurnSlotCount(1),
            TurnSlotWaitSeconds(10),
            lambda: ExternalServiceError("busy"),
        ),
    )
    first = threading.Thread(target=pipeline.start, args=(message("visitor_a"),))
    second = threading.Thread(target=pipeline.start, args=(message("visitor_b"),))
    first.start()
    assert wait_until(lambda: turns.started == ["visitor_a"])

    second.start()
    # The second turn waits for the only place; it has taken no lock (and
    # so no database connection) meanwhile.
    assert not wait_until(lambda: len(locks.taken) > 1, timeout=0.3)

    turns.gate.set()
    first.join(timeout=10)
    second.join(timeout=10)
    assert locks.taken == ["visitor_a", "visitor_b"]


def test_a_turn_beyond_the_places_is_refused_after_the_wait() -> None:
    slots = TurnSlotRegistry(
        TurnSlotCount(1),
        TurnSlotWaitSeconds(1),
        lambda: RateLimitedError("busy", retry_after_seconds=RetryAfterSeconds(5)),
    )

    with slots.hold(), pytest.raises(RateLimitedError), slots.hold():
        pass

    # The place came back: the next turn gets it.
    with slots.hold():
        pass


def test_customer_turns_get_as_many_places_as_model_calls() -> None:
    settings = assemble_app_settings({"LLM_MAX_CONCURRENCY": "2"})
    slots = build_customer_turn_slots(settings)

    with slots.hold(), slots.hold():
        refused = threading.Event()

        def third() -> None:
            try:
                with slots.hold():
                    pass
            except ExternalServiceError:
                refused.set()

        thread = threading.Thread(target=third, daemon=True)
        thread.start()
        # It waits (a customer turn waits long rather than fail).
        assert not refused.wait(0.3)

    thread.join(timeout=5)
    assert not refused.is_set()


def test_the_test_chat_asks_to_try_again_when_its_places_are_taken() -> None:
    settings = assemble_app_settings({"TEST_CHAT_MAX_CONCURRENCY": "2"})
    slots = build_test_chat_slots(settings)
    taken = threading.Event()
    release = threading.Event()

    def owner() -> None:
        with slots.hold():
            taken.set()
            release.wait(timeout=10)

    others = [threading.Thread(target=owner, daemon=True) for _ in range(2)]
    for thread in others:
        thread.start()
    assert taken.wait(5)
    refusal: RateLimitedError = refuse_busy_test_chat()
    release.set()
    for thread in others:
        thread.join(timeout=5)

    assert TurnSlotWaitSeconds(10) == TEST_CHAT_SLOT_WAIT
    assert refusal.retry_after_seconds == RetryAfterSeconds(5)
    assert "try again" in str(refusal)
