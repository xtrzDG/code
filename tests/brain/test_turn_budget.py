"""
A reply turn stops before another model round past the conversation's
token budget, past the turn's time, or when the model repeats a refused
tool call (AI-09); the conversation then goes to a colleague.
"""

import json
from datetime import timedelta

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.llm_scripts import ScriptedLlmTurn, ScriptedToolCall
from app.schemas.typings.conversations.strings import (
    LlmProviderPayload,
    LlmToolInputJson,
    MessageText,
)
from app.use_cases.conversations.replies.turn_budget import (
    CONVERSATION_TOKEN_BUDGET,
    MAX_IDENTICAL_TOOL_CALLS,
    TURN_WALL_CLOCK_LIMIT,
)
from tests.brain.brain_world import build_world
from tests.brain.engine_helpers import CountingLlmAdapter, requests_of
from tests.brain.manual_clock import ManualClock
from tests.brain.scripted_turns import call_tool, say, scripted

SEARCH: str = '{"query": "khinkali", "language": null}'
SAME_SEARCH_REORDERED: str = '{"language": null, "query": "khinkali"}'


def searches(*inputs: str) -> ScriptedLlmTurn:
    return ScriptedLlmTurn(
        tool_calls=[
            ScriptedToolCall(
                tool_name=AssistantToolName.SEARCH_KNOWLEDGE,
                input_json=LlmToolInputJson(text),
            )
            for text in inputs
        ]
    )


def test_a_call_repeated_too_often_is_refused_but_the_turn_goes_on() -> None:
    world = build_world(
        scripted(
            searches(SEARCH, SAME_SEARCH_REORDERED, SEARCH),
            say("Khinkali are on the menu."),
        )
    )

    reply = world.send("Do you have khinkali?")

    assert reply.text is not None and reply.text.endswith("Khinkali are on the menu.")
    assert len(world.search_knowledge.requests) == MAX_IDENTICAL_TOOL_CALLS
    assert [call.is_error for call in reply.tool_calls] == [False, False, True]
    refused = json.loads(str(reply.tool_calls[-1].result_json))
    assert "already called 2 times with this same input" in refused["error"]


def test_a_model_that_repeats_a_refused_call_is_stopped() -> None:
    world = build_world(
        scripted(
            searches(SEARCH, SEARCH, SEARCH),
            searches(SEARCH),
            say("never"),
        )
    )

    reply = world.send("Do you have khinkali?")

    assert len(requests_of(world)) == 2
    assert reply.is_handed_off is True
    assert reply.text is not None and "never" not in reply.text
    (handoff,) = world.handoffs()
    assert handoff.summary_code is HandoffSummaryCode.ANSWER_UNFINISHED


def test_past_the_conversations_token_budget_the_model_is_not_asked() -> None:
    per_call: int = CONVERSATION_TOKEN_BUDGET // 2
    llm = CountingLlmAdapter(
        scripted(say("Yes."), say("Sure."), say("never")),
        input_tokens=per_call,
        output_tokens=1,
    )
    world = build_world(llm)

    first = world.send("Do you have a terrace?")
    second = world.send("Is it heated?")
    third = world.send("And blankets?")

    assert first.is_handed_off is False
    assert second.is_handed_off is False
    assert len(llm.inner.requests) == 2
    assert third.is_handed_off is True
    assert third.text is not None and "never" not in third.text
    (handoff,) = world.handoffs()
    assert handoff.summary_code is HandoffSummaryCode.ANSWER_UNFINISHED


class SlowModel(LlmAdapterContract):
    """A scripted model each of whose answers takes longer than a turn may."""

    def __init__(self, inner: ScriptedLlmAdapter) -> None:
        self.inner: ScriptedLlmAdapter = inner
        self.clock: ManualClock | None = None

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self.inner.build_user_text_turn(text)

    def build_tool_results_turn(
        self, results: list[LlmToolResult]
    ) -> LlmProviderPayload:
        return self.inner.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        assert self.clock is not None
        self.clock.advance(TURN_WALL_CLOCK_LIMIT + timedelta(seconds=1))
        return self.inner.complete(request)


def test_no_round_starts_after_the_turns_time() -> None:
    llm = SlowModel(
        scripted(call_tool(AssistantToolName.SEARCH_KNOWLEDGE, SEARCH), say("never"))
    )
    world = build_world(llm)
    llm.clock = world.clock

    reply = world.send("Do you have khinkali?")

    assert len(llm.inner.requests) == 1
    assert reply.is_handed_off is True
    assert reply.text is not None and "never" not in reply.text
