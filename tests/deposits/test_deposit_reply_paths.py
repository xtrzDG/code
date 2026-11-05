"""
A deposit asked in a turn always reaches the customer with its payment
line: under a reply that passed the guard, and under the engine's handoff
text when the turn failed (the guard held the reply back twice, the model
ran out of rounds or the provider failed). Saying until when the place is
held, as the tool asks, never trips the deposit guard, even when the hold
ends on another day.
"""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import ReplyGuardVerdict
from app.schemas.dto.conversations import AssistantReply
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import call_tool, say, scripted
from tests.deposits.deposit_reply_fakes import PAYMENT_LINE, IssuingPaymentLink

ASK_LINK: ScriptedLlmTurn = call_tool(AssistantToolName.SEND_PAYMENT_LINK, "{}")
# A guest in the United Kingdom writes in English.
ENGLISH_GUEST: str = "447911123456"


def deposit_world(
    *turns: ScriptedLlmTurn,
    tool_round_limit: int = 4,
    held_until: str = "21:00",
) -> tuple[BrainWorld, IssuingPaymentLink]:
    payment_link = IssuingPaymentLink(held_until=held_until)
    world = build_world(
        scripted(*turns),
        tools=[AssistantToolName.CREATE_BOOKING],
        tool_round_limit=tool_round_limit,
        payment_link=payment_link,
    )
    return world, payment_link


def stored_texts(world: BrainWorld, reply: AssistantReply) -> list[str]:
    return [str(message.text) for message in world.messages(reply.conversation_id)]


def assert_line_delivered(world: BrainWorld, reply: AssistantReply) -> None:
    assert reply.text is not None
    assert str(reply.text).count(PAYMENT_LINE) == 1
    assert str(reply.text).endswith(PAYMENT_LINE)
    assert sum(PAYMENT_LINE in text for text in stored_texts(world, reply)) == 1


def test_a_reply_that_passed_carries_the_line_once() -> None:
    world, payment_link = deposit_world(ASK_LINK, say("Готово, держим столик."))

    reply = world.send("Хочу оплатить депозит")

    assert len(payment_link.calls) == 1
    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert "Готово, держим столик." in str(reply.text)
    assert_line_delivered(world, reply)


def test_a_handed_off_reply_still_carries_the_line() -> None:
    world, payment_link = deposit_world(
        ASK_LINK,
        say("Депозит 50 ₾, держим столик."),
        say("Хорошо: депозит 40 ₾, держим столик."),
    )

    reply = world.send("Хочу оплатить депозит")

    assert len(payment_link.calls) == 1
    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.is_handed_off
    assert "50 ₾" not in str(reply.text) and "40 ₾" not in str(reply.text)
    assert_line_delivered(world, reply)
    assert len(world.handoffs()) == 1


def test_a_turn_out_of_rounds_still_carries_the_line() -> None:
    world, payment_link = deposit_world(ASK_LINK, tool_round_limit=1)

    reply = world.send("Хочу оплатить депозит")

    assert len(payment_link.calls) == 1
    assert reply.is_handed_off
    assert_line_delivered(world, reply)


def test_a_provider_failure_after_the_link_still_carries_it() -> None:
    # The scripted model has nothing after the tool call: the provider fails.
    world, payment_link = deposit_world(ASK_LINK)

    reply = world.send("Хочу оплатить депозит")

    assert len(payment_link.calls) == 1
    assert reply.is_handed_off
    assert_line_delivered(world, reply)


def test_a_failed_turn_without_a_deposit_has_no_line() -> None:
    world, payment_link = deposit_world()

    reply = world.send("Хочу оплатить депозит")

    assert payment_link.calls == []
    assert reply.is_handed_off
    assert PAYMENT_LINE not in str(reply.text)


def test_a_hold_that_ends_tomorrow_passes_the_guard() -> None:
    sentence = (
        "We are holding your table until Wed, Oct 14, 11:00; it is confirmed "
        "once the deposit is paid."
    )
    world, _ = deposit_world(
        ASK_LINK, say(sentence), say(sentence), held_until="Wed, Oct 14, 11:00"
    )

    reply = world.send("Hi, I want to pay the deposit", user_id=ENGLISH_GUEST)

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert not reply.is_handed_off
    assert sentence in str(reply.text)
    assert_line_delivered(world, reply)
    assert world.handoffs() == []
