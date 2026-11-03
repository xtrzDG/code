"""
One model response runs at most five tool calls (the others are answered
with an error the model can act on), and a turn stops before a further
model round once the business is past its hard spend limit: the
application wires the spend check into the customer's turn (autotests play
without it).
"""

import json

from app.containers.app import AppContainer
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.spend import SpendLevel
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.conversations.strings import LlmToolInputJson
from app.use_cases.conversations.replies.round_limits import (
    MAX_TOOL_CALLS_PER_RESPONSE,
)
from app.use_cases.spend_guard.check_business_spend_use_case import (
    CheckBusinessSpendUseCase,
)
from tests.brain.brain_orchestrators import GuardOptions
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import call_tool, say, scripted
from tests.spend_guard.test_spend_turns import FixedSpendCheck

SEARCH: str = '{"query": "khinkali", "language": null}'


def many_searches(count: int) -> ScriptedLlmTurn:
    """Searches for different dishes (a repeated one is refused on its own)."""

    return ScriptedLlmTurn(
        tool_calls=[
            ScriptedToolCall(
                tool_name=AssistantToolName.SEARCH_KNOWLEDGE,
                input_json=LlmToolInputJson(
                    f'{{"query": "khinkali {number}", "language": null}}'
                ),
            )
            for number in range(count)
        ]
    )


def test_calls_past_the_limit_of_a_response_never_run() -> None:
    world = build_world(scripted(many_searches(7), say("Khinkali are on the menu.")))

    reply = world.send("Do you have khinkali?")

    assert reply.text is not None and reply.text.endswith("Khinkali are on the menu.")
    assert len(world.search_knowledge.requests) == MAX_TOOL_CALLS_PER_RESPONSE
    assert [call.is_error for call in reply.tool_calls] == [
        *([False] * MAX_TOOL_CALLS_PER_RESPONSE),
        True,
        True,
    ]
    refused = json.loads(str(reply.tool_calls[-1].result_json))
    assert "at most 5 tools" in refused["error"]


def test_a_turn_stops_before_another_round_past_the_hard_limit() -> None:
    spend = FixedSpendCheck(SpendLevel.HARD_LIMIT)
    world = build_world(
        scripted(call_tool(AssistantToolName.SEARCH_KNOWLEDGE, SEARCH), say("never")),
        guard=GuardOptions(round_spend_check=spend),
    )

    reply = world.send("Do you have khinkali?")

    assert len(requests_of(world)) == 1
    assert len(spend.requests) == 1
    assert reply.is_handed_off is True
    assert reply.text is not None and "never" not in reply.text
    assert len(world.handoffs()) == 1


def test_under_the_limit_every_later_round_is_checked() -> None:
    spend = FixedSpendCheck(SpendLevel.NORMAL)
    world = build_world(
        scripted(
            call_tool(AssistantToolName.SEARCH_KNOWLEDGE, SEARCH),
            call_tool(AssistantToolName.SEARCH_KNOWLEDGE, SEARCH),
            say("Khinkali are on the menu."),
        ),
        guard=GuardOptions(round_spend_check=spend),
    )

    reply = world.send("Do you have khinkali?")

    assert reply.text is not None and reply.text.endswith("Khinkali are on the menu.")
    assert len(requests_of(world)) == 3
    assert [str(request.model_id) for request in spend.requests] == [
        "scripted",
        "scripted",
    ]


def spend_check_of(orchestrator: object) -> object:
    """The spend check the orchestrator's reply generation was wired with."""

    generate_reply: object = vars(orchestrator)["_generate_reply"]
    return vars(generate_reply)["_check_spend"]


def test_the_application_checks_the_spend_of_customer_turns_only() -> None:
    orchestrators = AppContainer().orchestrators.conversations

    customer = spend_check_of(orchestrators.conversation_turn_orchestrator())
    autotest = spend_check_of(orchestrators.autotest_turn_orchestrator())

    assert isinstance(customer, CheckBusinessSpendUseCase)
    assert autotest is None
