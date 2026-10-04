"""The scripted model plays a scenario's reference conversation by role."""

import json

import pytest

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_PERSONA_OPENING,
    DONE_MARKER,
    JUDGE_SYSTEM_PROMPT,
)
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.scripted_model import ScenarioScript, build_scripted_adapter
from tests.evals.eval_builders import llm_request, user_turn

ASSISTANT_TURN: str = json.dumps({"role": "assistant", "content": []})
HANDOFF_RESULT: str = json.dumps(
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": json.dumps({"customer_message": "A colleague will reply."}),
            }
        ],
    }
)


def spec() -> ScenarioSpec:
    return ScenarioSpec.model_validate(
        {
            "id": "human__en",
            "language": "en",
            "kind": "human_request",
            "persona": {"name": "Emma"},
            "customer": ["I want a person.", "Thanks."],
            "assistant": [
                {"call": {"handoff_to_human": {"reason": "customer_request"}}},
                {"say_result": "customer_message"},
                {"say_result": "missing_field"},
            ],
        }
    )


def script() -> ScenarioScript:
    return ScenarioScript(spec())


def test_the_judge_scores_everything_five() -> None:
    answer = script().respond(llm_request([user_turn("x")], JUDGE_SYSTEM_PROMPT))

    assert set(json.loads(str(answer.text))["scores"].values()) == {5}


def test_the_customer_says_its_messages_then_done() -> None:
    persona = f"{CUSTOMER_PERSONA_OPENING} of the business."
    played = script()

    assert played.respond(llm_request([user_turn("Start")], persona)).text == (
        "I want a person."
    )
    second = llm_request([user_turn("Start"), ASSISTANT_TURN, user_turn("Ok")], persona)
    assert played.respond(second).text == "Thanks."
    third = llm_request(
        [user_turn("a"), ASSISTANT_TURN, user_turn("b"), ASSISTANT_TURN], persona
    )
    assert played.respond(third).text == DONE_MARKER


def test_the_assistant_plays_its_steps_in_order() -> None:
    adapter = build_scripted_adapter(spec())
    first = adapter.complete(llm_request([user_turn("I want a person.")]))
    second = adapter.complete(
        llm_request([user_turn("I want a person."), ASSISTANT_TURN, HANDOFF_RESULT])
    )

    assert [str(call.tool_name) for call in first.tool_calls] == ["handoff_to_human"]
    assert second.text == "A colleague will reply."


def test_a_missing_result_field_or_step_fails_loudly() -> None:
    played = script()
    two_turns = [user_turn("a"), ASSISTANT_TURN, user_turn("b"), ASSISTANT_TURN]

    with pytest.raises(ExternalServiceError, match="no text field 'missing_field'"):
        played.respond(llm_request([*two_turns, user_turn("c")]))

    with pytest.raises(ExternalServiceError, match="has no assistant step 4"):
        played.respond(llm_request([*two_turns, user_turn("c"), ASSISTANT_TURN]))
