import json
from typing import Any

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.conversations import LlmTurnRole, ReplyGuardVerdict
from app.schemas.constants.handoffs import HandoffReason
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import MessageText
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.business_setups import ARMENIA, ISRAEL, knowledge_item
from tests.brain.scripted_turns import call_tool, say, scripted


def last_user_turn_text(world: BrainWorld, request_index: int) -> str:
    assert isinstance(world.llm, ScriptedLlmAdapter)
    payload = world.llm.requests[request_index].transcript[-1]
    content: list[dict[str, Any]] = json.loads(payload)["content"]
    return "".join(block.get("text", "") for block in content)


def test_prices_from_facts_and_tools_pass_the_guard() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khinkali"}'),
            say("Хинкали — 1,20 лари за штуку, хачапури — 18 ₾."),
        )
    )

    reply = world.send("Сколько стоят хинкали?")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN
    assert reply.text is not None
    assert reply.text.endswith("Хинкали — 1,20 лари за штуку, хачапури — 18 ₾.")


def test_an_invented_price_is_rewritten_once() -> None:
    world = build_world(
        scripted(say("Хачапури стоит 25 лари."), say("Хачапури стоит 18 лари."))
    )

    reply = world.send("Сколько стоит хачапури?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert reply.text.endswith("Хачапури стоит 18 лари.")
    note = last_user_turn_text(world, 1)
    assert "not in the fact table" in note
    assert "25 лари" in note
    turns = world.turns(reply.conversation_id)
    assert [turn.role for turn in turns] == [
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
        LlmTurnRole.USER,
        LlmTurnRole.ASSISTANT,
    ]
    assert world.handoffs() == []


def test_a_reply_still_inventing_numbers_is_replaced_by_a_handoff() -> None:
    world = build_world(
        scripted(
            say("Скидка 20% и депозит 50 ₾."),
            say("Хорошо: скидка 15% и депозит 40 ₾."),
        )
    )

    reply = world.send("Дадите скидку?")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert reply.is_handed_off is True
    assert reply.text is not None
    assert reply.text.endswith("[ru] A colleague will reply soon.")
    assert "%" not in reply.text
    handoff = world.handoffs()[0]
    assert handoff.reason is HandoffReason.UNVERIFIED_NUMBERS
    assert "15%" in handoff.summary
    assert "40 ₾" in handoff.summary
    stored = world.messages(reply.conversation_id)[-1]
    assert "50 ₾" not in stored.text


def test_a_failing_rewrite_is_handed_off_too() -> None:
    answers: list[ScriptedLlmTurn] = [
        ScriptedLlmTurn(text=MessageText("Table at 21:45 is free."))
    ]

    def respond(request: LlmRequest) -> ScriptedLlmTurn:
        if answers:
            return answers.pop(0)

        raise ExternalServiceError("timeout")

    world = build_world(ScriptedLlmAdapter(respond))

    reply = world.send("Any table tonight?")

    assert reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert world.handoffs()[0].reason is HandoffReason.UNVERIFIED_NUMBERS


def test_the_rewrite_may_check_with_a_tool() -> None:
    world = build_world(
        scripted(
            say("We have a table at 21:00."),
            call_tool(
                AssistantToolName.CHECK_AVAILABILITY,
                '{"resource_type":null,"date":"2026-10-01","time":null,'
                '"party_size":2,"duration_minutes":null,"nights":null}',
            ),
            say("Today there are tables at 19:30 and 20:00."),
        )
    )

    reply = world.send("A table for 2 tonight?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert reply.text is not None
    assert reply.text.endswith("Today there are tables at 19:30 and 20:00.")


def test_values_the_customer_gave_and_earlier_tool_results_are_allowed() -> None:
    world = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khachapuri"}'),
            say("Adjarian khachapuri is 18 GEL."),
            say("Yes, 18 GEL each; for your 7 guests at 21:15 we will prepare them."),
        )
    )

    world.send("Price of khachapuri?")
    reply = world.send("Ok, we are 7 people, coming at 21:15. Same price?")

    assert reply.guard_verdict is ReplyGuardVerdict.CLEAN


def test_the_guard_understands_shekels_and_drams() -> None:
    israel = build_world(
        scripted(say("המנה עולה 18 ₪."), say("המנה עולה 45 ₪."), say("שוב 45 ₪.")),
        ISRAEL,
        knowledge=[knowledge_item("Shakshuka", 4500, "ILS", "‏45.00 ₪")],
        facts=[("opening_hours", "Opening hours", "Sun-Thu 08:00-22:00")],
    )
    armenia = build_world(
        scripted(
            call_tool(AssistantToolName.GET_PRICE, '{"item_name":"khorovats"}'),
            say("Խորովածը 4 500 դրամ է։"),
        ),
        ARMENIA,
        knowledge=[knowledge_item("Khorovats", 450_000, "AMD")],
    )

    shekel_reply = israel.send("כמה עולה שקשוקה?")
    dram_reply = armenia.send("Խորովածն ինչ արժե՞")

    assert shekel_reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
    assert israel.handoffs()[0].reason is HandoffReason.UNVERIFIED_NUMBERS
    assert dram_reply.guard_verdict is ReplyGuardVerdict.CLEAN


def test_a_discount_the_customer_asked_for_is_not_confirmed() -> None:
    world = build_world(
        scripted(
            say("Конечно, скидка 10% для вас."),
            say("Скидки назначает менеджер, могу передать ваш вопрос."),
        )
    )

    reply = world.send("Сделаете скидку 10%?")

    assert reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    assert "10%" in last_user_turn_text(world, 1)
    assert reply.text is not None
    assert reply.text.endswith("могу передать ваш вопрос.")
